"""Store-scoped finance setup and automatic operational ledger posting."""

from __future__ import annotations

import hashlib
import json
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import or_

from app.extensions import db
from app.models.document_sequence import _next_document_number
from app.models.finance import (
    CurrentAccount,
    CurrentEntry,
    CurrentSettlement,
    FinanceAccount,
    FinanceActivation,
    FinanceCategory,
    FinanceMovement,
    FinancePaymentMapping,
    FinanceSourceState,
    FinanceTransfer,
    MonthlyOverheadBudget,
    ObligationRecurrencePlan,
    ObligationPayment,
    PosReconciliation,
    ShortTermObligation,
)
from app.services.product_inventory import get_customer_gross_amount
from app.services.user_auth import get_current_user
from app.utils import now_in_istanbul, quantize_amount, utc_to_istanbul


class FinanceConfigurationError(ValueError):
    """Raised when an activated store cannot create a complete ledger entry."""


class InsufficientFinanceBalanceError(FinanceConfigurationError):
    """Carry balance details so routes can redact them for operational users."""

    def __init__(self, account, available_balance, required_amount, alternative_account_names):
        self.account_name = account.name
        self.available_balance = _money(available_balance)
        self.required_amount = _money(required_amount)
        self.alternative_account_names = tuple(alternative_account_names)
        super().__init__(
            "{} hesabında iade/değişim için yeterli bakiye yok. "
            "Kullanılabilir bakiye: {}; müşteriye yapılacak net ödeme: {}. "
            "Önce bu hesaba transfer yapın veya yeterli bakiyesi olan başka bir "
            "iade ödeme hesabı seçin. İşlem kaydedilmedi.".format(
                self.account_name,
                _format_try_amount(self.available_balance),
                _format_try_amount(self.required_amount),
            )
        )

    def message_for_user(self, *, disclose_amounts):
        if disclose_amounts:
            return str(self)
        message = (
            f"{self.account_name} hesabında bu iade/değişim için yeterli bakiye bulunmuyor."
        )
        if self.alternative_account_names:
            alternatives = ", ".join(self.alternative_account_names)
            message += f" Yeterli bakiyesi olan hesaplar: {alternatives}."
        else:
            message += " Yeterli bakiyesi olan başka bir hesap bulunmuyor."
        return (
            f"{message} Uygun bir hesap seçin veya yöneticinizden ilgili hesaba bakiye "
            "aktarımı yapmasını isteyin. İşlem kaydedilmedi."
        )


DEFAULT_ACCOUNTS = (
    ("CASH", "02", "Nakit Kasa", "cash"),
    ("BANK", "01", "Banka/EFT", "bank"),
    ("POS", "03", "POS/Kart Alacağı", "pos_receivable"),
)

DEFAULT_CATEGORIES = (
    ("OPENING", "Devir Bakiyesi", "in"),
    ("SALE", "Satış Tahsilatı", "in"),
    ("RETURN", "İade Ödemesi", "out"),
    ("EXCHANGE_RETURN", "Değişim Eski Ürün İadesi", "out"),
    ("EXCHANGE_REPLACEMENT", "Değişim Yeni Ürün Bedeli", "in"),
    ("TRANSFER", "Hesaplar Arası Transfer", "both"),
    ("POS_RECONCILIATION", "POS Mutabakatı", "both"),
    ("POS_COMMISSION", "POS Komisyonu", "out"),
    ("MANUAL_IN", "Manuel Gelir", "in"),
    ("MANUAL_OUT", "Manuel Gider", "out"),
    ("CURRENT", "Cari Tahsilat / Ödeme", "both"),
    ("OBLIGATION", "Kısa Vadeli Borç Ödemesi", "out"),
)

DEFAULT_PAYMENT_ACCOUNT_CODES = {
    "Nakit": "CASH",
    "Havale/EFT": "BANK",
    "Kredi Kartı": "POS",
}

CURRENT_ACCOUNT_CATEGORIES = {
    "customer": {"label": "Müşteri", "prefix": "120", "sequence": "current_customer"},
    "supplier": {"label": "Tedarikçi", "prefix": "320", "sequence": "current_supplier"},
}


def ensure_default_finance_setup(site_id, store_id):
    """Create missing system accounts, categories and standard payment mappings."""
    accounts = {}
    for code, display_code, name, account_type in DEFAULT_ACCOUNTS:
        account = FinanceAccount.query.filter_by(
            site_id=site_id,
            store_id=store_id,
            code=code,
        ).one_or_none()
        if account is None:
            account = FinanceAccount(
                site_id=site_id,
                store_id=store_id,
                code=code,
                display_code=display_code,
                name=name,
                account_type=account_type,
                is_system=True,
                is_active=True,
            )
            db.session.add(account)
        elif not str(account.display_code or "").strip() or account.display_code == "-":
            account.display_code = display_code
        accounts[code] = account

    categories = {}
    for code, name, direction in DEFAULT_CATEGORIES:
        category = FinanceCategory.query.filter_by(site_id=site_id, code=code).one_or_none()
        if category is None:
            category = FinanceCategory(
                site_id=site_id,
                code=code,
                name=name,
                direction=direction,
                default_is_overhead=False,
                is_system=True,
                is_active=True,
            )
            db.session.add(category)
        categories[code] = category

    db.session.flush()
    for payment_method, account_code in DEFAULT_PAYMENT_ACCOUNT_CODES.items():
        mapping = FinancePaymentMapping.query.filter_by(
            site_id=site_id,
            store_id=store_id,
            payment_method=payment_method,
        ).one_or_none()
        if mapping is None:
            db.session.add(
                FinancePaymentMapping(
                    site_id=site_id,
                    store_id=store_id,
                    payment_method=payment_method,
                    account_id=accounts[account_code].id,
                )
            )

    return accounts, categories


def activate_finance(site_id, store_id, opening_cash=Decimal("0.00"), activated_at=None, actor_id=None):
    """Activate finance for one store and post its initial cash opening balance."""
    existing = FinanceActivation.query.filter_by(site_id=site_id, store_id=store_id).one_or_none()
    if existing is not None:
        raise FinanceConfigurationError("Bu mağaza için Finans Yönetimi zaten etkin.")

    accounts, categories = ensure_default_finance_setup(site_id, store_id)
    activated_at = activated_at or datetime.utcnow()
    actor_id = actor_id if actor_id is not None else _current_user_id()
    activation = FinanceActivation(
        site_id=site_id,
        store_id=store_id,
        activated_at=activated_at,
        activated_by_user_id=actor_id,
    )
    db.session.add(activation)

    amount = _money(opening_cash)
    if amount < Decimal("0.00"):
        raise FinanceConfigurationError("Devir bakiyesi negatif olamaz.")
    if amount > Decimal("0.00"):
        db.session.add(
            FinanceMovement(
                site_id=site_id,
                store_id=store_id,
                account_id=accounts["CASH"].id,
                category_id=categories["OPENING"].id,
                occurred_at=activated_at,
                direction="in",
                amount=amount,
                movement_type="opening_balance",
                description="Finans Yönetimi açılış devir bakiyesi",
                document_no="DEVIR",
                source_type="finance_activation",
                source_id=None,
                source_key=f"finance-activation:{site_id}:{store_id}:opening",
                pair_key=f"activation:{site_id}:{store_id}",
                created_by_user_id=actor_id,
            )
        )
    return activation


def get_finance_activation(site_id, store_id):
    return FinanceActivation.query.filter_by(site_id=site_id, store_id=store_id).one_or_none()


def ensure_finance_period_open(site_id, store_id, occurred_on):
    """Reject writes dated in a closed business day until a manager reopens it."""
    from app.models.finance_operations import DailyCashClosing

    if isinstance(occurred_on, datetime):
        business_date = utc_to_istanbul(occurred_on).date()
    else:
        business_date = _as_date(occurred_on)
    if business_date is None:
        business_date = now_in_istanbul().date()
    closing = DailyCashClosing.query.filter_by(
        site_id=site_id,
        store_id=store_id,
        business_date=business_date,
        status="closed",
    ).one_or_none()
    if closing is not None:
        raise FinanceConfigurationError(
            f"{business_date.strftime('%d.%m.%Y')} günü kapatılmış. İşlem için önce günü yönetici olarak yeniden açın."
        )
    return business_date


def sync_sale_finance(sale):
    """Post or revise one completed sale in the activated store ledger."""
    if sale.id is None:
        db.session.flush()
    activation = get_finance_activation(sale.site_id, sale.store_id)
    if activation is None or _as_naive_utc(_sale_occurred_at(sale)) < _as_naive_utc(activation.activated_at):
        return None
    ensure_finance_period_open(sale.site_id, sale.store_id, _sale_occurred_at(sale))

    account = _mapped_account(sale.site_id, sale.store_id, sale.payment_method)
    amount = _money(sale.total_amount)
    fingerprint = _fingerprint(
        {
            "amount": str(amount),
            "payment_method": sale.payment_method,
            "account_id": account.id,
            "revision_no": int(sale.revision_no or 1),
            "order_status": sale.order_status,
        }
    )
    state, changed = _prepare_source_revision(
        sale.site_id,
        sale.store_id,
        "sale",
        sale.id,
        fingerprint,
        _sale_occurred_at(sale),
    )
    if not changed:
        return state.last_movement_id

    last_movement = None
    if amount > Decimal("0.00"):
        category = _category(sale.site_id, "SALE")
        last_movement = _append_movement(
            site_id=sale.site_id,
            store_id=sale.store_id,
            account=account,
            category=category,
            occurred_at=_sale_occurred_at(sale),
            direction="in",
            amount=amount,
            movement_type="sale",
            description=f"Satış #{sale.document_no or sale.id}",
            document_no=str(sale.document_no or sale.id),
            source_type="sale",
            source_id=sale.id,
            source_key=f"sale:{sale.id}:v{state.version}:main",
            pair_key=f"sale:{sale.id}:v{state.version}",
        )
    state.last_movement_id = last_movement.id if last_movement else None
    return state.last_movement_id


def sync_return_finance(return_record, refund_account_id=None):
    """Post return outflow and exchange replacement inflow as separate entries."""
    if return_record.id is None:
        db.session.flush()
    activation = get_finance_activation(return_record.site_id, return_record.store_id)
    occurred_at = return_record.return_date or datetime.utcnow()
    if activation is None or _as_naive_utc(occurred_at) < _as_naive_utc(activation.activated_at):
        return None
    ensure_finance_period_open(return_record.site_id, return_record.store_id, occurred_at)

    account = _return_account(return_record, refund_account_id)
    returned_total = Decimal("0.00")
    replacement_total = Decimal("0.00")
    for item in return_record.items:
        gross = item.gross_refund_amount
        if gross is None:
            gross = get_customer_gross_amount(item.refund_amount or Decimal("0.00"))
        gross = _money(gross)
        if gross > Decimal("0.00"):
            returned_total += gross
        elif gross < Decimal("0.00"):
            replacement_total += abs(gross)
    returned_total = _money(returned_total)
    replacement_total = _money(replacement_total)
    is_exchange = return_record.type == "degisim"
    net_difference = _money(returned_total - replacement_total)
    net_customer_outflow = max(
        net_difference,
        Decimal("0.00"),
    )
    exchange_summary = None
    if is_exchange:
        if net_difference > Decimal("0.00"):
            exchange_summary = f"Net fark iadesi: {_format_try_amount(net_difference)}"
        elif net_difference < Decimal("0.00"):
            exchange_summary = (
                f"Net fark tahsilatı: {_format_try_amount(abs(net_difference))}"
            )
        else:
            exchange_summary = "Net fark: ₺0,00"

    fingerprint = _fingerprint(
        {
            "account_id": account.id,
            "returned_total": str(returned_total),
            "replacement_total": str(replacement_total),
            "type": return_record.type,
            "item_count": len(return_record.items),
        }
    )
    account = _lock_finance_account(account)
    state, changed = _prepare_source_revision(
        return_record.site_id,
        return_record.store_id,
        "return",
        return_record.id,
        fingerprint,
        occurred_at,
    )
    if not changed:
        return state.last_movement_id

    available_balance = get_account_balance(account)
    if net_customer_outflow > available_balance:
        raise InsufficientFinanceBalanceError(
            account,
            available_balance,
            net_customer_outflow,
            _sufficient_alternative_account_names(account, net_customer_outflow),
        )

    pair_key = f"return:{return_record.id}:v{state.version}"
    last_movement = None
    if returned_total > Decimal("0.00"):
        refund_description = (
            f"Değişim eski ürün iadesi #{return_record.document_no or return_record.id}"
            if is_exchange
            else f"İade #{return_record.document_no or return_record.id}"
        )
        if exchange_summary:
            refund_description = f"{refund_description} · {exchange_summary}"
        last_movement = _append_movement(
            site_id=return_record.site_id,
            store_id=return_record.store_id,
            account=account,
            category=_category(
                return_record.site_id,
                "EXCHANGE_RETURN" if is_exchange else "RETURN",
            ),
            occurred_at=occurred_at,
            direction="out",
            amount=returned_total,
            movement_type="return",
            description=refund_description,
            document_no=str(return_record.document_no or return_record.id),
            source_type="return",
            source_id=return_record.id,
            source_key=f"return:{return_record.id}:v{state.version}:refund",
            pair_key=pair_key,
        )
    if replacement_total > Decimal("0.00"):
        replacement_description = (
            f"Değişim yeni ürün bedeli #{return_record.document_no or return_record.id}"
        )
        if exchange_summary:
            replacement_description = f"{replacement_description} · {exchange_summary}"
        last_movement = _append_movement(
            site_id=return_record.site_id,
            store_id=return_record.store_id,
            account=account,
            category=_category(return_record.site_id, "EXCHANGE_REPLACEMENT"),
            occurred_at=occurred_at,
            direction="in",
            amount=replacement_total,
            movement_type="exchange_sale",
            description=replacement_description,
            document_no=str(return_record.document_no or return_record.id),
            source_type="return",
            source_id=return_record.id,
            source_key=f"return:{return_record.id}:v{state.version}:replacement",
            pair_key=pair_key,
        )
    state.last_movement_id = last_movement.id if last_movement else None
    return state.last_movement_id


def get_account_balance(account):
    """Return the immutable ledger balance for one finance account."""
    movements = FinanceMovement.query.filter_by(
        site_id=account.site_id,
        store_id=account.store_id,
        account_id=account.id,
    ).all()
    balance = sum(
        (movement.amount if movement.direction == "in" else -movement.amount for movement in movements),
        Decimal("0.00"),
    )
    return quantize_amount(balance)


def create_finance_account(*, site_id, store_id, code, name, account_type):
    """Create an additional store account without replacing system accounts."""
    _require_activation(site_id, store_id)
    normalized_code = str(code or "").strip().upper()
    normalized_name = str(name or "").strip()
    if not normalized_code or not normalized_name:
        raise FinanceConfigurationError("Hesap kodu ve adı zorunludur.")
    if account_type not in {"cash", "bank", "pos_receivable"}:
        raise FinanceConfigurationError("Hesap türü geçerli değil.")
    if FinanceAccount.query.filter(
        FinanceAccount.site_id == site_id,
        FinanceAccount.store_id == store_id,
        or_(
            FinanceAccount.code == normalized_code,
            FinanceAccount.display_code == normalized_code,
        ),
    ).first():
        raise FinanceConfigurationError("Bu hesap kodu mağazada zaten kullanılıyor.")
    account = FinanceAccount(
        site_id=site_id,
        store_id=store_id,
        code=normalized_code,
        display_code=normalized_code,
        name=normalized_name,
        account_type=account_type,
        is_system=False,
    )
    db.session.add(account)
    db.session.flush()
    return account


def create_finance_category(*, site_id, code, name, direction, default_is_overhead=False):
    """Create a user category while preserving the protected system catalog."""
    normalized_code = str(code or "").strip().upper()
    normalized_name = str(name or "").strip()
    if not normalized_code or not normalized_name:
        raise FinanceConfigurationError("Kategori kodu ve adı zorunludur.")
    if direction not in {"in", "out", "both"}:
        raise FinanceConfigurationError("Kategori yönü geçerli değil.")
    default_is_overhead = bool(default_is_overhead)
    if default_is_overhead and direction == "in":
        raise FinanceConfigurationError("Gelir kategorisi varsayılan genel gider olamaz.")
    if FinanceCategory.query.filter_by(site_id=site_id, code=normalized_code).first():
        raise FinanceConfigurationError("Bu kategori kodu site içinde zaten kullanılıyor.")
    category = FinanceCategory(
        site_id=site_id,
        code=normalized_code,
        name=normalized_name,
        direction=direction,
        default_is_overhead=default_is_overhead,
        is_system=False,
    )
    db.session.add(category)
    db.session.flush()
    return category


def update_finance_category_overhead_default(*, site_id, category_id, default_is_overhead):
    """Update the future transaction default without rewriting historical movements."""
    category = _category_by_id(site_id, category_id)
    if category.is_system:
        raise FinanceConfigurationError("Sistem kategorilerinin genel gider varsayılanı değiştirilemez.")
    normalized_default = bool(default_is_overhead)
    if normalized_default and category.direction == "in":
        raise FinanceConfigurationError("Gelir kategorisi varsayılan genel gider olamaz.")
    category.default_is_overhead = normalized_default
    db.session.flush()
    return category


def set_payment_mapping(*, site_id, store_id, payment_method, account_id):
    """Map one site payment method to an active account in the same store."""
    _require_activation(site_id, store_id)
    normalized_method = str(payment_method or "").strip()
    if not normalized_method:
        raise FinanceConfigurationError("Ödeme yöntemi zorunludur.")
    account = _account(site_id, store_id, account_id)
    mapping = FinancePaymentMapping.query.filter_by(
        site_id=site_id,
        store_id=store_id,
        payment_method=normalized_method,
    ).one_or_none()
    if mapping is None:
        mapping = FinancePaymentMapping(
            site_id=site_id,
            store_id=store_id,
            payment_method=normalized_method,
        )
        db.session.add(mapping)
    mapping.account_id = account.id
    db.session.flush()
    return mapping


def adjust_opening_balance(
    *,
    site_id,
    store_id,
    target_amount,
    reason=None,
    allow_after_activity=False,
):
    """Set the opening component without mutating an existing ledger row."""
    _require_activation(site_id, store_id)
    accounts, categories = ensure_default_finance_setup(site_id, store_id)
    cash_account = accounts["CASH"]
    opening_category = categories["OPENING"]
    target = _money(target_amount)
    if target < 0:
        raise FinanceConfigurationError("Devir bakiyesi negatif olamaz.")

    opening_movements = FinanceMovement.query.filter_by(
        site_id=site_id,
        store_id=store_id,
        account_id=cash_account.id,
        category_id=opening_category.id,
    ).all()
    current_opening = quantize_amount(
        sum(
            (
                movement.amount
                if movement.direction == "in"
                else -movement.amount
                for movement in opening_movements
            ),
            Decimal("0.00"),
        )
    )
    delta = quantize_amount(target - current_opening)
    if delta == Decimal("0.00"):
        return None

    has_normal_activity = (
        FinanceMovement.query.filter(
            FinanceMovement.site_id == site_id,
            FinanceMovement.store_id == store_id,
            FinanceMovement.category_id != opening_category.id,
        ).first()
        is not None
    )
    if has_normal_activity and not allow_after_activity:
        raise FinanceConfigurationError(
            "Normal finans hareketi bulunan mağazada devir tutarı yalnız düzeltme hareketiyle değiştirilebilir."
        )
    if has_normal_activity and not str(reason or "").strip():
        raise FinanceConfigurationError("Devir düzeltmesi için açıklama zorunludur.")

    return _append_movement(
        site_id=site_id,
        store_id=store_id,
        account=cash_account,
        category=opening_category,
        direction="in" if delta > 0 else "out",
        amount=abs(delta),
        occurred_at=datetime.utcnow(),
        movement_type="opening_adjustment",
        source_type="finance_activation",
        source_id=get_finance_activation(site_id, store_id).id,
        source_key=f"opening-adjustment:{site_id}:{store_id}:{uuid4().hex}",
        pair_key=f"opening-adjustment:{uuid4().hex}",
        description=str(reason or "Devir bakiyesi güncellemesi").strip(),
    )


def create_current_account(
    *,
    site_id,
    account_category="customer",
    name,
    tax_no=None,
    phone=None,
    email=None,
    note=None,
):
    normalized_category = str(account_category or "").strip().lower()
    normalized_name = str(name or "").strip()
    category_config = CURRENT_ACCOUNT_CATEGORIES.get(normalized_category)
    if category_config is None:
        raise FinanceConfigurationError("Cari kategorisi müşteri veya tedarikçi olmalıdır.")
    if not normalized_name:
        raise FinanceConfigurationError("Cari adı zorunludur.")

    connection = db.session.connection()
    while True:
        serial = _next_document_number(connection, site_id, category_config["sequence"])
        normalized_code = f"{category_config['prefix']}{serial:05d}"
        if not CurrentAccount.query.filter_by(site_id=site_id, code=normalized_code).first():
            break

    account = CurrentAccount(
        site_id=site_id,
        code=normalized_code,
        account_category=normalized_category,
        name=normalized_name,
        tax_no=str(tax_no or "").strip() or None,
        phone=str(phone or "").strip() or None,
        email=str(email or "").strip() or None,
        note=str(note or "").strip() or None,
    )
    db.session.add(account)
    db.session.flush()
    return account


def create_current_entry(
    *,
    site_id,
    store_id,
    current_account_id,
    entry_type,
    amount,
    due_date=None,
    description=None,
):
    _require_activation(site_id, store_id)
    current_account = db.session.get(CurrentAccount, current_account_id)
    if current_account is None or current_account.site_id != site_id:
        raise FinanceConfigurationError("Cari hesap bu siteye ait değil.")
    if entry_type not in {"receivable", "payable"}:
        raise FinanceConfigurationError("Cari kayıt türü alacak veya borç olmalıdır.")
    entry_amount = _money(amount)
    if entry_amount <= 0:
        raise FinanceConfigurationError("Cari kayıt tutarı sıfırdan büyük olmalıdır.")
    entry = CurrentEntry(
        site_id=site_id,
        store_id=store_id,
        current_account_id=current_account.id,
        entry_type=entry_type,
        amount=entry_amount,
        remaining_amount=entry_amount,
        due_date=due_date,
        description=str(description or "").strip() or None,
        status="open",
        created_by_user_id=_current_user_id(),
    )
    db.session.add(entry)
    db.session.flush()
    return entry


def settle_current_entry(
    *,
    site_id,
    store_id,
    entry_id,
    finance_account_id,
    amount,
    occurred_at,
    description=None,
):
    _require_activation(site_id, store_id)
    entry = CurrentEntry.query.filter_by(
        id=entry_id,
        site_id=site_id,
        store_id=store_id,
    ).first()
    if entry is None:
        raise FinanceConfigurationError("Cari kayıt bulunamadı.")
    settlement_amount = _money(amount)
    if settlement_amount <= 0 or settlement_amount > entry.remaining_amount:
        raise FinanceConfigurationError("Tahsilat/ödeme tutarı açık bakiyeyi aşamaz.")
    finance_account = _account(site_id, store_id, finance_account_id)
    category = _category(site_id, "CURRENT")
    direction = "in" if entry.entry_type == "receivable" else "out"
    source_key = f"current-settlement:{entry.id}:{uuid4().hex}"
    movement = _append_movement(
        site_id=site_id,
        store_id=store_id,
        account=finance_account,
        category=category,
        direction=direction,
        amount=settlement_amount,
        occurred_at=occurred_at,
        movement_type="current_settlement",
        source_type="current_entry",
        source_id=entry.id,
        source_key=source_key,
        pair_key=source_key,
        description=str(description or entry.description or "Cari tahsilat/ödeme").strip(),
        current_account_id=entry.current_account_id,
    )
    entry.remaining_amount = quantize_amount(entry.remaining_amount - settlement_amount)
    entry.status = "closed" if entry.remaining_amount == Decimal("0.00") else "partial"
    settlement = CurrentSettlement(
        site_id=site_id,
        store_id=store_id,
        current_entry_id=entry.id,
        finance_account_id=finance_account.id,
        amount=settlement_amount,
        occurred_at=_as_naive_utc(occurred_at),
        movement_id=movement.id,
        created_by_user_id=_current_user_id(),
    )
    db.session.add(settlement)
    return settlement


def create_short_term_obligation(
    *,
    site_id,
    store_id,
    category_id,
    title,
    amount,
    due_date,
    current_account_id=None,
    recurrence=None,
    recurrence_end_date=None,
    is_overhead=None,
    note=None,
):
    _require_activation(site_id, store_id)
    category = _category_by_id(site_id, category_id)
    if category.direction not in {"out", "both"}:
        raise FinanceConfigurationError("Borç kategorisi gider yönlü olmalıdır.")
    obligation_amount = _money(amount)
    if obligation_amount <= 0:
        raise FinanceConfigurationError("Borç tutarı sıfırdan büyük olmalıdır.")
    if current_account_id is not None:
        current_account = db.session.get(CurrentAccount, current_account_id)
        if current_account is None or current_account.site_id != site_id:
            raise FinanceConfigurationError("Cari hesap bu siteye ait değil.")
    normalized_recurrence = str(recurrence or "").strip() or "once"
    if normalized_recurrence not in {"once", "monthly", "weekly"}:
        raise FinanceConfigurationError("Borç tekrar seçimi geçerli değil.")
    normalized_due_date = _as_date(due_date)
    normalized_end_date = _as_date(recurrence_end_date)
    if normalized_recurrence != "once" and normalized_due_date is None:
        raise FinanceConfigurationError("Haftalık veya aylık planda ilk vade zorunludur.")
    if normalized_end_date is not None and normalized_recurrence == "once":
        raise FinanceConfigurationError("Bitiş tarihi yalnız tekrarlayan borçlarda kullanılabilir.")
    if normalized_end_date is not None and normalized_end_date < normalized_due_date:
        raise FinanceConfigurationError("Tekrar bitiş tarihi ilk vadeden önce olamaz.")

    title_value = str(title or "").strip()
    if not title_value:
        raise FinanceConfigurationError("Borç başlığı zorunludur.")
    overhead_value = (
        category.default_is_overhead
        if is_overhead is None
        else bool(is_overhead)
    )
    note_value = str(note or "").strip() or None
    created_by_user_id = _current_user_id()

    if normalized_recurrence == "once":
        obligation = ShortTermObligation(
            site_id=site_id,
            store_id=store_id,
            current_account_id=current_account_id,
            category_id=category.id,
            title=title_value,
            amount=obligation_amount,
            remaining_amount=obligation_amount,
            due_date=normalized_due_date,
            recurrence="once",
            is_overhead=overhead_value,
            status="open",
            note=note_value,
            created_by_user_id=created_by_user_id,
        )
        db.session.add(obligation)
        db.session.flush()
        return obligation

    plan = ObligationRecurrencePlan(
        site_id=site_id,
        store_id=store_id,
        current_account_id=current_account_id,
        category_id=category.id,
        title=title_value,
        amount=obligation_amount,
        recurrence=normalized_recurrence,
        first_due_date=normalized_due_date,
        next_due_date=_next_recurrence_date(
            normalized_due_date,
            normalized_recurrence,
            normalized_due_date.day,
        ),
        anchor_day=normalized_due_date.day,
        next_sequence=2,
        end_date=normalized_end_date,
        is_overhead=overhead_value,
        status="active",
        note=note_value,
        created_by_user_id=created_by_user_id,
    )
    if plan.end_date is not None and plan.next_due_date > plan.end_date:
        plan.status = "completed"
    db.session.add(plan)
    db.session.flush()

    obligation = _build_recurring_obligation(
        plan,
        due_date=normalized_due_date,
        sequence=1,
    )
    db.session.add(obligation)
    db.session.flush()
    return obligation


def sync_recurring_obligations(*, through_date=None, site_id=None, store_id=None):
    """Materialize due recurrence periods exactly once and return the created count."""
    normalized_through_date = _as_date(through_date) or now_in_istanbul().date()
    query = ObligationRecurrencePlan.query.filter(
        ObligationRecurrencePlan.status == "active",
        ObligationRecurrencePlan.next_due_date <= normalized_through_date,
    )
    if site_id is not None:
        query = query.filter(ObligationRecurrencePlan.site_id == site_id)
    if store_id is not None:
        query = query.filter(ObligationRecurrencePlan.store_id == store_id)

    plans = query.order_by(ObligationRecurrencePlan.id.asc()).with_for_update().all()
    created_count = 0
    for plan in plans:
        generated_for_plan = 0
        while plan.next_due_date <= normalized_through_date:
            if plan.end_date is not None and plan.next_due_date > plan.end_date:
                plan.status = "completed"
                break
            generated_for_plan += 1
            if generated_for_plan > 5200:
                raise FinanceConfigurationError(
                    f"{plan.title} tekrar planında güvenli dönem sınırı aşıldı."
                )

            occurrence = ShortTermObligation.query.filter_by(
                recurrence_plan_id=plan.id,
                due_date=plan.next_due_date,
            ).one_or_none()
            if occurrence is None:
                occurrence = _build_recurring_obligation(
                    plan,
                    due_date=plan.next_due_date,
                    sequence=plan.next_sequence,
                )
                db.session.add(occurrence)
                created_count += 1
            plan.next_sequence = max(
                plan.next_sequence,
                (occurrence.recurrence_sequence or plan.next_sequence) + 1,
            )
            plan.next_due_date = _next_recurrence_date(
                plan.next_due_date,
                plan.recurrence,
                plan.anchor_day,
            )
            if plan.end_date is not None and plan.next_due_date > plan.end_date:
                plan.status = "completed"
                break

    db.session.flush()
    return created_count


def update_obligation_recurrence_plan(
    *,
    site_id,
    store_id,
    plan_id,
    amount,
    end_date=None,
):
    plan = ObligationRecurrencePlan.query.filter_by(
        id=plan_id,
        site_id=site_id,
        store_id=store_id,
    ).one_or_none()
    if plan is None:
        raise FinanceConfigurationError("Tekrarlayan borç planı bulunamadı.")

    plan_amount = _money(amount)
    if plan_amount <= 0:
        raise FinanceConfigurationError("Gelecek dönem tutarı sıfırdan büyük olmalıdır.")
    normalized_end_date = _as_date(end_date)
    if normalized_end_date is not None and normalized_end_date < plan.first_due_date:
        raise FinanceConfigurationError("Tekrar bitiş tarihi ilk vadeden önce olamaz.")

    plan.amount = plan_amount
    plan.end_date = normalized_end_date
    if plan.status != "stopped":
        if normalized_end_date is not None and plan.next_due_date > normalized_end_date:
            plan.status = "completed"
        elif plan.status == "completed":
            plan.status = "active"
    db.session.flush()
    return plan


def stop_obligation_recurrence_plan(*, site_id, store_id, plan_id):
    plan = ObligationRecurrencePlan.query.filter_by(
        id=plan_id,
        site_id=site_id,
        store_id=store_id,
    ).one_or_none()
    if plan is None:
        raise FinanceConfigurationError("Tekrarlayan borç planı bulunamadı.")
    if plan.status != "active":
        raise FinanceConfigurationError("Yalnız aktif tekrar planı durdurulabilir.")
    plan.status = "stopped"
    plan.stopped_at = datetime.utcnow()
    db.session.flush()
    return plan


def resume_obligation_recurrence_plan(
    *,
    site_id,
    store_id,
    plan_id,
    resumed_on=None,
):
    plan = (
        ObligationRecurrencePlan.query.filter_by(
            id=plan_id,
            site_id=site_id,
            store_id=store_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if plan is None:
        raise FinanceConfigurationError("Tekrarlayan borç planı bulunamadı.")
    if plan.status != "stopped":
        raise FinanceConfigurationError("Yalnız durdurulmuş tekrar planı devam ettirilebilir.")

    target_date = _as_date(resumed_on) or now_in_istanbul().date()
    next_due_date = plan.next_due_date
    while next_due_date < target_date:
        next_due_date = _next_recurrence_date(
            next_due_date,
            plan.recurrence,
            plan.anchor_day,
        )
    if plan.end_date is not None and next_due_date > plan.end_date:
        raise FinanceConfigurationError(
            "Planın bitiş tarihi devam edilecek ilk vadeden önce. "
            "Önce bitiş tarihini güncelleyin."
        )

    plan.next_due_date = next_due_date
    plan.status = "active"
    plan.stopped_at = None
    db.session.flush()
    return plan


def pay_short_term_obligation(
    *,
    site_id,
    store_id,
    obligation_id,
    finance_account_id,
    amount,
    occurred_at,
    description=None,
):
    _require_activation(site_id, store_id)
    obligation = ShortTermObligation.query.filter_by(
        id=obligation_id,
        site_id=site_id,
        store_id=store_id,
    ).first()
    if obligation is None:
        raise FinanceConfigurationError("Kısa vadeli borç bulunamadı.")
    payment_amount = _money(amount)
    if payment_amount <= 0 or payment_amount > obligation.remaining_amount:
        raise FinanceConfigurationError("Ödeme tutarı açık borç bakiyesini aşamaz.")
    finance_account = _account(site_id, store_id, finance_account_id)
    category = _category(site_id, "OBLIGATION")
    source_key = f"obligation-payment:{obligation.id}:{uuid4().hex}"
    movement = _append_movement(
        site_id=site_id,
        store_id=store_id,
        account=finance_account,
        category=category,
        direction="out",
        amount=payment_amount,
        occurred_at=occurred_at,
        movement_type="obligation_payment",
        source_type="short_term_obligation",
        source_id=obligation.id,
        source_key=source_key,
        pair_key=source_key,
        description=str(description or obligation.title).strip(),
        current_account_id=obligation.current_account_id,
        is_overhead=obligation.is_overhead,
    )
    obligation.remaining_amount = quantize_amount(obligation.remaining_amount - payment_amount)
    obligation.status = "paid" if obligation.remaining_amount == Decimal("0.00") else "partial"
    payment = ObligationPayment(
        site_id=site_id,
        store_id=store_id,
        obligation_id=obligation.id,
        finance_account_id=finance_account.id,
        amount=payment_amount,
        occurred_at=_as_naive_utc(occurred_at),
        movement_id=movement.id,
        created_by_user_id=_current_user_id(),
    )
    db.session.add(payment)
    return payment


def upsert_monthly_overhead_budget(
    *,
    site_id,
    store_id,
    budget_month,
    category_id,
    amount,
    note=None,
):
    _require_activation(site_id, store_id)
    category = _category_by_id(site_id, category_id)
    if category.direction not in {"out", "both"}:
        raise FinanceConfigurationError("Genel gider kategorisi gider yönlü olmalıdır.")
    if isinstance(budget_month, datetime):
        budget_month = budget_month.date()
    if not isinstance(budget_month, date):
        raise FinanceConfigurationError("Bütçe ayı geçerli bir tarih olmalıdır.")
    normalized_month = budget_month.replace(day=1)
    budget_amount = _money(amount)
    if budget_amount < 0:
        raise FinanceConfigurationError("Aylık genel gider negatif olamaz.")
    budget = MonthlyOverheadBudget.query.filter_by(
        site_id=site_id,
        store_id=store_id,
        budget_month=normalized_month,
        category_id=category.id,
    ).first()
    if budget is None:
        budget = MonthlyOverheadBudget(
            site_id=site_id,
            store_id=store_id,
            budget_month=normalized_month,
            category_id=category.id,
        )
        db.session.add(budget)
    budget.amount = budget_amount
    budget.note = str(note or "").strip() or None
    budget.created_by_user_id = budget.created_by_user_id or _current_user_id()
    db.session.flush()
    return budget


def create_manual_movement(
    *,
    site_id,
    store_id,
    account_id,
    category_id,
    direction,
    amount,
    occurred_at,
    description,
    document_no=None,
    current_account_id=None,
    is_overhead=None,
):
    _require_activation(site_id, store_id)
    ensure_finance_period_open(site_id, store_id, occurred_at)
    account = _account(site_id, store_id, account_id)
    category = _category_by_id(site_id, category_id)
    if current_account_id is not None:
        current_account = db.session.get(CurrentAccount, current_account_id)
        if current_account is None or current_account.site_id != site_id:
            raise FinanceConfigurationError("Cari hesap bu siteye ait değil.")
    if direction not in {"in", "out"}:
        raise FinanceConfigurationError("Manuel hareket yönü gelir veya gider olmalıdır.")
    if category.direction not in {direction, "both"}:
        raise FinanceConfigurationError("Kategori seçilen hareket yönüyle uyumlu değil.")
    is_overhead = (
        bool(category.default_is_overhead) and direction == "out"
        if is_overhead is None
        else bool(is_overhead)
    )
    if is_overhead and direction != "out":
        raise FinanceConfigurationError("Genel gider işareti yalnız gider hareketlerinde kullanılabilir.")
    normalized_description = str(description or "").strip()
    if not normalized_description:
        raise FinanceConfigurationError("Manuel hareket açıklaması zorunludur.")
    movement = _append_movement(
        site_id=site_id,
        store_id=store_id,
        account=account,
        category=category,
        occurred_at=occurred_at,
        direction=direction,
        amount=amount,
        movement_type="manual",
        description=normalized_description,
        document_no=document_no,
        source_type="manual",
        source_id=None,
        source_key=f"manual:{uuid4().hex}",
        pair_key=f"manual:{uuid4().hex}",
        current_account_id=current_account_id,
        is_overhead=is_overhead,
    )
    return movement


def reverse_movement(movement, reason, occurred_at=None):
    """Correct an immutable movement by appending its exact opposite."""
    _require_activation(movement.site_id, movement.store_id)
    normalized_reason = str(reason or "").strip()
    if not normalized_reason:
        raise FinanceConfigurationError("Ters kayıt nedeni zorunludur.")
    if movement.reversal_of_id is not None:
        raise FinanceConfigurationError("Bir ters kayıt yeniden ters çevrilemez.")
    existing = FinanceMovement.query.filter_by(reversal_of_id=movement.id).one_or_none()
    if existing is not None:
        return existing
    return _append_movement(
        site_id=movement.site_id,
        store_id=movement.store_id,
        account=movement.account,
        category=movement.category,
        occurred_at=occurred_at or datetime.utcnow(),
        direction="out" if movement.direction == "in" else "in",
        amount=movement.amount,
        movement_type="reversal",
        description=f"Ters kayıt: {normalized_reason}",
        document_no=movement.document_no,
        source_type=movement.source_type,
        source_id=movement.source_id,
        source_key=f"movement:{movement.id}:reversal",
        pair_key=movement.pair_key,
        reversal_of_id=movement.id,
        current_account_id=movement.current_account_id,
        is_overhead=movement.is_overhead,
    )


def create_account_transfer(
    *, site_id, store_id, from_account_id, to_account_id, amount, occurred_at, description=None
):
    _require_activation(site_id, store_id)
    source = _account(site_id, store_id, from_account_id)
    target = _account(site_id, store_id, to_account_id)
    amount = _money(amount)
    if source.id == target.id:
        raise FinanceConfigurationError("Transfer hesapları birbirinden farklı olmalıdır.")
    if amount <= Decimal("0.00"):
        raise FinanceConfigurationError("Transfer tutarı sıfırdan büyük olmalıdır.")
    if get_account_balance(source) < amount:
        raise FinanceConfigurationError("Kaynak hesap bakiyesi transfer için yetersiz.")

    pair_key = f"transfer:{uuid4().hex}"
    transfer = FinanceTransfer(
        site_id=site_id,
        store_id=store_id,
        from_account_id=source.id,
        to_account_id=target.id,
        amount=amount,
        occurred_at=occurred_at,
        description=description,
        pair_key=pair_key,
        created_by_user_id=_current_user_id(),
    )
    db.session.add(transfer)
    db.session.flush()
    category = _category(site_id, "TRANSFER")
    for account, direction, suffix in ((source, "out", "out"), (target, "in", "in")):
        _append_movement(
            site_id=site_id,
            store_id=store_id,
            account=account,
            category=category,
            occurred_at=occurred_at,
            direction=direction,
            amount=amount,
            movement_type="transfer",
            description=description or "Hesaplar arası transfer",
            document_no=str(transfer.id),
            source_type="transfer",
            source_id=transfer.id,
            source_key=f"{pair_key}:{suffix}",
            pair_key=pair_key,
        )
    return transfer


def create_pos_reconciliation(
    *, site_id, store_id, pos_account_id, bank_account_id, gross_amount,
    commission_rate, occurred_at, reference=None
):
    _require_activation(site_id, store_id)
    pos_account = _account(site_id, store_id, pos_account_id)
    bank_account = _account(site_id, store_id, bank_account_id)
    gross = _money(gross_amount)
    rate = _commission_rate(commission_rate)
    commission = _money((gross * rate) / Decimal("100"))
    net = _money(gross - commission)
    if pos_account.account_type != "pos_receivable" or bank_account.account_type != "bank":
        raise FinanceConfigurationError("Mutabakat için POS alacağı ve banka hesabı seçilmelidir.")
    if gross <= Decimal("0.00"):
        raise FinanceConfigurationError("POS brüt tutarı sıfırdan büyük olmalıdır.")
    if rate < Decimal("0.0000") or rate >= Decimal("100.0000"):
        raise FinanceConfigurationError("Komisyon oranı %0 ile %100 arasında olmalıdır.")
    if commission < Decimal("0.00") or net <= Decimal("0.00"):
        raise FinanceConfigurationError("POS mutabakat tutarları geçerli değil.")
    if get_account_balance(pos_account) < gross:
        raise FinanceConfigurationError("POS alacağı bakiyesi mutabakat için yetersiz.")

    pair_key = f"pos:{uuid4().hex}"
    reconciliation = PosReconciliation(
        site_id=site_id,
        store_id=store_id,
        pos_account_id=pos_account.id,
        bank_account_id=bank_account.id,
        gross_amount=gross,
        commission_rate=rate,
        commission_amount=commission,
        net_amount=net,
        occurred_at=occurred_at,
        reference=reference,
        pair_key=pair_key,
        created_by_user_id=_current_user_id(),
    )
    db.session.add(reconciliation)
    db.session.flush()
    transfer_category = _category(site_id, "POS_RECONCILIATION")
    for account, direction, suffix in ((pos_account, "out", "pos"), (bank_account, "in", "bank")):
        _append_movement(
            site_id=site_id, store_id=store_id, account=account,
            category=transfer_category, occurred_at=occurred_at, direction=direction,
            amount=net, movement_type="pos_reconciliation",
            description=reference or "POS mutabakatı", document_no=str(reconciliation.id),
            source_type="pos_reconciliation", source_id=reconciliation.id,
            source_key=f"{pair_key}:{suffix}", pair_key=pair_key,
        )
    if commission > Decimal("0.00"):
        _append_movement(
            site_id=site_id, store_id=store_id, account=pos_account,
            category=_category(site_id, "POS_COMMISSION"), occurred_at=occurred_at,
            direction="out", amount=commission, movement_type="pos_commission",
            description=f"POS komisyonu: {reference or reconciliation.id}",
            document_no=str(reconciliation.id), source_type="pos_reconciliation",
            source_id=reconciliation.id, source_key=f"{pair_key}:commission", pair_key=pair_key,
            is_overhead=False,
        )
    return reconciliation


def _prepare_source_revision(site_id, store_id, source_type, source_id, fingerprint, occurred_at):
    state = FinanceSourceState.query.filter_by(
        site_id=site_id,
        store_id=store_id,
        source_type=source_type,
        source_id=source_id,
    ).one_or_none()
    if state is None:
        state = FinanceSourceState(
            site_id=site_id,
            store_id=store_id,
            source_type=source_type,
            source_id=source_id,
            fingerprint=fingerprint,
            version=1,
        )
        db.session.add(state)
        db.session.flush()
        return state, True
    if state.fingerprint == fingerprint:
        return state, False

    _reverse_source_version(state, occurred_at)
    state.version = int(state.version or 1) + 1
    state.fingerprint = fingerprint
    state.last_movement_id = None
    state.updated_at = datetime.utcnow()
    return state, True


def _reverse_source_version(state, occurred_at):
    pair_key = f"{state.source_type}:{state.source_id}:v{state.version}"
    originals = FinanceMovement.query.filter_by(
        site_id=state.site_id,
        store_id=state.store_id,
        pair_key=pair_key,
        reversal_of_id=None,
    ).order_by(FinanceMovement.id.asc()).all()
    for original in originals:
        already_reversed = FinanceMovement.query.filter_by(reversal_of_id=original.id).first()
        if already_reversed is not None:
            continue
        _append_movement(
            site_id=original.site_id,
            store_id=original.store_id,
            account=original.account,
            category=original.category,
            occurred_at=occurred_at,
            direction="out" if original.direction == "in" else "in",
            amount=original.amount,
            movement_type="reversal",
            description=f"Ters kayıt: {original.description or original.source_key}",
            document_no=original.document_no,
            source_type=state.source_type,
            source_id=state.source_id,
            source_key=f"{original.source_key}:reversal",
            pair_key=f"{pair_key}:reversal",
            reversal_of_id=original.id,
            is_overhead=original.is_overhead,
        )


def _append_movement(
    *,
    site_id,
    store_id,
    account,
    category,
    occurred_at,
    direction,
    amount,
    movement_type,
    description,
    source_type,
    source_id,
    source_key,
    pair_key,
    document_no=None,
    reversal_of_id=None,
    current_account_id=None,
    is_overhead=False,
):
    amount = _money(amount)
    if amount <= Decimal("0.00"):
        raise FinanceConfigurationError("Finans hareket tutarı sıfırdan büyük olmalıdır.")
    existing = FinanceMovement.query.filter_by(
        site_id=site_id,
        store_id=store_id,
        source_key=source_key,
    ).one_or_none()
    if existing is not None:
        expected = (
            account.id,
            category.id,
            direction,
            amount,
            movement_type,
            source_type,
            source_id,
            reversal_of_id,
            current_account_id,
            bool(is_overhead),
        )
        actual = (
            existing.account_id,
            existing.category_id,
            existing.direction,
            existing.amount,
            existing.movement_type,
            existing.source_type,
            existing.source_id,
            existing.reversal_of_id,
            existing.current_account_id,
            bool(existing.is_overhead),
        )
        if actual != expected:
            raise FinanceConfigurationError("Finans kaynak anahtarı farklı bir hareket için kullanılmış.")
        return existing
    movement = FinanceMovement(
        site_id=site_id,
        store_id=store_id,
        account_id=account.id,
        category_id=category.id,
        occurred_at=_as_naive_utc(occurred_at),
        direction=direction,
        amount=amount,
        movement_type=movement_type,
        description=description,
        document_no=document_no,
        source_type=source_type,
        source_id=source_id,
        source_key=source_key,
        pair_key=pair_key,
        reversal_of_id=reversal_of_id,
        current_account_id=current_account_id,
        is_overhead=bool(is_overhead),
        created_by_user_id=_current_user_id(),
    )
    db.session.add(movement)
    db.session.flush()
    return movement


def _mapped_account(site_id, store_id, payment_method):
    mapping = FinancePaymentMapping.query.filter_by(
        site_id=site_id,
        store_id=store_id,
        payment_method=(payment_method or "").strip(),
    ).one_or_none()
    if mapping is None or mapping.account is None or not mapping.account.is_active:
        raise FinanceConfigurationError(
            f"'{payment_method or '-'}' ödeme yöntemi için aktif finans hesabı eşlemesi bulunamadı."
        )
    return mapping.account


def _require_activation(site_id, store_id):
    activation = get_finance_activation(site_id, store_id)
    if activation is None:
        raise FinanceConfigurationError("Bu mağaza için Finans Yönetimi henüz aktive edilmedi.")
    return activation


def _account(site_id, store_id, account_id):
    account = FinanceAccount.query.filter_by(
        id=account_id,
        site_id=site_id,
        store_id=store_id,
        is_active=True,
    ).one_or_none()
    if account is None:
        raise FinanceConfigurationError("Seçilen finans hesabı bu mağazada aktif değil.")
    return account


def _lock_finance_account(account):
    """Serialize balance-consuming operations for one store account."""
    locked_account = (
        FinanceAccount.query.filter_by(
            id=account.id,
            site_id=account.site_id,
            store_id=account.store_id,
            is_active=True,
        )
        .with_for_update()
        .one_or_none()
    )
    if locked_account is None:
        raise FinanceConfigurationError("Seçilen finans hesabı bu mağazada aktif değil.")
    return locked_account


def _sufficient_alternative_account_names(account, required_amount):
    alternatives = FinanceAccount.query.filter(
        FinanceAccount.site_id == account.site_id,
        FinanceAccount.store_id == account.store_id,
        FinanceAccount.is_active.is_(True),
        FinanceAccount.id != account.id,
    ).order_by(FinanceAccount.name.asc()).all()
    return tuple(
        candidate.name
        for candidate in alternatives
        if get_account_balance(candidate) >= required_amount
    )


def _category_by_id(site_id, category_id):
    category = FinanceCategory.query.filter_by(
        id=category_id,
        site_id=site_id,
        is_active=True,
    ).one_or_none()
    if category is None:
        raise FinanceConfigurationError("Seçilen finans kategorisi bu site için aktif değil.")
    return category


def _return_account(return_record, refund_account_id):
    if refund_account_id is not None:
        account = FinanceAccount.query.filter_by(
            id=refund_account_id,
            site_id=return_record.site_id,
            store_id=return_record.store_id,
            is_active=True,
        ).one_or_none()
        if account is None:
            raise FinanceConfigurationError("Seçilen iade ödeme hesabı bu mağazada aktif değil.")
        return account

    sale_state = FinanceSourceState.query.filter_by(
        site_id=return_record.site_id,
        store_id=return_record.store_id,
        source_type="sale",
        source_id=return_record.original_sale_id,
    ).one_or_none()
    if sale_state is not None:
        pair_key = f"sale:{return_record.original_sale_id}:v{sale_state.version}"
        movement = FinanceMovement.query.filter_by(
            site_id=return_record.site_id,
            store_id=return_record.store_id,
            pair_key=pair_key,
            reversal_of_id=None,
            direction="in",
        ).order_by(FinanceMovement.id.desc()).first()
        if movement is not None:
            return movement.account
    return _mapped_account(
        return_record.site_id,
        return_record.store_id,
        return_record.original_sale.payment_method,
    )


def _category(site_id, code):
    category = FinanceCategory.query.filter_by(site_id=site_id, code=code, is_active=True).one_or_none()
    if category is None:
        raise FinanceConfigurationError(f"'{code}' finans kategorisi aktif değil.")
    return category


def _sale_occurred_at(sale):
    return sale.completed_at or sale.sale_date or datetime.utcnow()


def _as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise FinanceConfigurationError("Tekrar planı tarihi geçerli değil.") from exc


def _next_recurrence_date(current_due_date, recurrence, anchor_day):
    if recurrence == "weekly":
        return current_due_date + timedelta(days=7)
    if recurrence != "monthly":
        raise FinanceConfigurationError("Tekrar planı periyodu geçerli değil.")
    if current_due_date.month == 12:
        year, month = current_due_date.year + 1, 1
    else:
        year, month = current_due_date.year, current_due_date.month + 1
    return date(year, month, min(anchor_day, monthrange(year, month)[1]))


def _build_recurring_obligation(plan, *, due_date, sequence):
    return ShortTermObligation(
        site_id=plan.site_id,
        store_id=plan.store_id,
        current_account_id=plan.current_account_id,
        category_id=plan.category_id,
        title=plan.title,
        amount=plan.amount,
        remaining_amount=plan.amount,
        due_date=due_date,
        recurrence=plan.recurrence,
        recurrence_plan_id=plan.id,
        recurrence_sequence=sequence,
        is_overhead=plan.is_overhead,
        status="open",
        note=plan.note,
        created_by_user_id=plan.created_by_user_id,
    )


def _current_user_id():
    user = get_current_user()
    return user.id if user is not None else None


def _money(value):
    if value is None:
        return Decimal("0.00")
    return quantize_amount(value)


def _format_try_amount(value):
    amount = _money(value)
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"₺{formatted}"


def _commission_rate(value):
    if value is None:
        return Decimal("0.0000")
    rate = Decimal(value)
    if not rate.is_finite():
        raise FinanceConfigurationError("Komisyon oranı geçerli değil.")
    return rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _fingerprint(payload):
    serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _as_naive_utc(value):
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
