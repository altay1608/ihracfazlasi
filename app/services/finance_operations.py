"""High-level, staff-friendly workflows for daily accounting operations."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import (
    CurrentAccount,
    DailyCashClosing,
    ExpenseVoucher,
    FinanceAccount,
    FinanceApproval,
    FinanceCategory,
    FinanceMovement,
    PersonnelAdvanceSettlement,
    PersonnelFinanceRecord,
    Product,
    StoreInventory,
    SupplierInvoice,
    SupplierInvoiceLine,
)
from app.services.finance import (
    FinanceConfigurationError,
    create_current_entry,
    create_manual_movement,
    ensure_finance_period_open,
    get_account_balance,
)
from app.services.inventory_history import record_inventory_movement
from app.services.user_auth import get_current_user
from app.utils import istanbul_day_start_utc, quantize_amount


def _money(value):
    try:
        return quantize_amount(Decimal(str(value or 0)))
    except Exception as exc:
        raise FinanceConfigurationError("Tutar geçerli değil.") from exc


def _user_id():
    user = get_current_user()
    return user.id if user else None


def _daily_account_total(site_id, store_id, code, business_date):
    account = FinanceAccount.query.filter_by(site_id=site_id, store_id=store_id, code=code).one_or_none()
    if account is None:
        return Decimal("0.00")
    start = istanbul_day_start_utc(business_date)
    end = istanbul_day_start_utc(business_date + timedelta(days=1))
    movements = FinanceMovement.query.filter(
        FinanceMovement.site_id == site_id,
        FinanceMovement.store_id == store_id,
        FinanceMovement.account_id == account.id,
        FinanceMovement.occurred_at >= start,
        FinanceMovement.occurred_at < end,
    ).all()
    return quantize_amount(sum(
        (row.amount if row.direction == "in" else -row.amount for row in movements),
        Decimal("0.00"),
    ))


def closing_expectations(site_id, store_id, business_date):
    cash = FinanceAccount.query.filter_by(site_id=site_id, store_id=store_id, code="CASH").one_or_none()
    return {
        "cash": get_account_balance(cash) if cash else Decimal("0.00"),
        "card": _daily_account_total(site_id, store_id, "POS", business_date),
        "transfer": _daily_account_total(site_id, store_id, "BANK", business_date),
    }


def create_daily_closing(*, site_id, store_id, business_date, counted_cash, counted_card,
                         counted_transfer, handover_from, handover_to=None, note=None):
    existing = DailyCashClosing.query.filter_by(
        site_id=site_id, store_id=store_id, business_date=business_date
    ).first()
    if existing is not None and existing.status == "closed":
        raise FinanceConfigurationError("Bu tarih için gün sonu kapanışı zaten yapılmış.")
    handover_from = str(handover_from or "").strip()
    if not handover_from:
        raise FinanceConfigurationError("Kasayı teslim eden personel zorunludur.")
    expected = closing_expectations(site_id, store_id, business_date)
    values = {
        "cash": _money(counted_cash),
        "card": _money(counted_card),
        "transfer": _money(counted_transfer),
    }
    closing = existing or DailyCashClosing(site_id=site_id, store_id=store_id, business_date=business_date)
    closing.expected_cash, closing.counted_cash = expected["cash"], values["cash"]
    closing.cash_difference = quantize_amount(values["cash"] - expected["cash"])
    closing.expected_card, closing.counted_card = expected["card"], values["card"]
    closing.card_difference = quantize_amount(values["card"] - expected["card"])
    closing.expected_transfer, closing.counted_transfer = expected["transfer"], values["transfer"]
    closing.transfer_difference = quantize_amount(values["transfer"] - expected["transfer"])
    closing.handover_from = handover_from
    closing.handover_to = str(handover_to or "").strip() or None
    closing.note = str(note or "").strip() or None
    closing.closed_by_user_id = _user_id()
    closing.closed_at = datetime.utcnow()
    closing.status = "closed"
    db.session.add(closing)
    return closing


def reopen_daily_closing(closing, reason):
    reason = str(reason or "").strip()
    if closing.status != "closed":
        raise FinanceConfigurationError("Bu gün zaten açık durumda.")
    if len(reason) < 5:
        raise FinanceConfigurationError("Yeniden açma nedeni en az 5 karakter olmalıdır.")
    closing.status = "reopened"
    closing.reopened_by_user_id = _user_id()
    closing.reopened_at = datetime.utcnow()
    closing.reopen_reason = reason
    return closing


def _approval_limit(config):
    return _money(config.get("FINANCE_APPROVAL_LIMIT", "5000"))


def _queue_approval(entity_type, entity, title):
    approval = FinanceApproval(
        site_id=entity.site_id,
        store_id=entity.store_id,
        entity_type=entity_type,
        entity_id=entity.id,
        title=title,
        amount=entity.gross_amount if entity_type == "expense" else entity.amount,
        requested_by_user_id=_user_id(),
    )
    db.session.add(approval)
    return approval


def _post_expense(voucher):
    movement = create_manual_movement(
        site_id=voucher.site_id,
        store_id=voucher.store_id,
        account_id=voucher.account_id,
        category_id=voucher.category_id,
        direction="out",
        amount=voucher.gross_amount,
        occurred_at=datetime.combine(voucher.expense_date, time(hour=12)),
        description=voucher.description,
        document_no=voucher.document_no,
        is_overhead=True,
    )
    voucher.movement_id = movement.id
    voucher.status = "approved"
    voucher.decided_at = datetime.utcnow()
    return movement


def create_expense(*, site_id, store_id, account_id, category_id, expense_date, vendor,
                   document_no, description, net_amount, vat_amount, config):
    ensure_finance_period_open(site_id, store_id, expense_date)
    account = FinanceAccount.query.filter_by(
        id=account_id, site_id=site_id, store_id=store_id, is_active=True
    ).one_or_none()
    category = FinanceCategory.query.filter_by(
        id=category_id, site_id=site_id, is_active=True
    ).one_or_none()
    if account is None or category is None or category.direction not in {"out", "both"}:
        raise FinanceConfigurationError("Geçerli bir gider hesabı ve kategorisi seçmelisiniz.")
    net = _money(net_amount)
    vat = _money(vat_amount)
    if net < 0 or vat < 0:
        raise FinanceConfigurationError("Net ve KDV tutarları negatif olamaz.")
    gross = quantize_amount(net + vat)
    if gross <= 0:
        raise FinanceConfigurationError("Masraf toplamı sıfırdan büyük olmalıdır.")
    voucher = ExpenseVoucher(
        site_id=site_id, store_id=store_id, account_id=account_id, category_id=category_id,
        expense_date=expense_date, vendor=str(vendor or "").strip() or None,
        document_no=str(document_no or "").strip() or None,
        description=str(description or "").strip(), net_amount=net, vat_amount=vat,
        gross_amount=gross, requested_by_user_id=_user_id(),
    )
    if not voucher.description:
        raise FinanceConfigurationError("Masraf açıklaması zorunludur.")
    db.session.add(voucher)
    db.session.flush()
    if gross > _approval_limit(config):
        _queue_approval("expense", voucher, f"Masraf: {voucher.description}")
    else:
        _post_expense(voucher)
    return voucher


def create_supplier_invoice(*, site_id, store_id, supplier_id, invoice_no, invoice_date,
                            due_date, net_amount, vat_amount, note=None, line_items=None,
                            product_id=None, quantity=0, unit_cost=0):
    ensure_finance_period_open(site_id, store_id, invoice_date)
    supplier = db.session.get(CurrentAccount, supplier_id)
    if supplier is None or supplier.site_id != site_id or supplier.account_category != "supplier" or not supplier.is_active:
        raise FinanceConfigurationError("Geçerli bir tedarikçi seçmelisiniz.")
    invoice_no = str(invoice_no or "").strip()
    if not invoice_no:
        raise FinanceConfigurationError("Fatura numarası zorunludur.")
    net, vat = _money(net_amount), _money(vat_amount)
    if net < 0 or vat < 0:
        raise FinanceConfigurationError("Net ve KDV tutarları negatif olamaz.")
    gross = quantize_amount(net + vat)
    if gross <= 0:
        raise FinanceConfigurationError("Fatura toplamı sıfırdan büyük olmalıdır.")
    entry = create_current_entry(
        site_id=site_id, store_id=store_id, current_account_id=supplier.id,
        entry_type="payable", amount=gross, due_date=due_date,
        description=f"Alış faturası {invoice_no}",
    )
    invoice = SupplierInvoice(
        site_id=site_id, store_id=store_id, supplier_id=supplier.id,
        invoice_no=invoice_no, invoice_date=invoice_date, due_date=due_date,
        net_amount=net, vat_amount=vat, gross_amount=gross,
        current_entry_id=entry.id, note=str(note or "").strip() or None,
        created_by_user_id=_user_id(),
    )
    db.session.add(invoice)
    db.session.flush()

    normalized_lines = list(line_items or [])
    if not normalized_lines and product_id:
        normalized_lines = [{"product_id": product_id, "quantity": quantity, "unit_cost": unit_cost}]
    stock_line_total = Decimal("0.00")
    for item in normalized_lines:
        selected_product_id = item.get("product_id")
        if not selected_product_id:
            continue
        product = Product.query.filter_by(id=int(selected_product_id), site_id=site_id).one_or_none()
        qty, cost = int(item.get("quantity") or 0), _money(item.get("unit_cost"))
        if product is None or qty <= 0 or cost < 0:
            raise FinanceConfigurationError("Stok satırı bilgileri geçerli değil.")
        invoice.lines.append(SupplierInvoiceLine(
            product_id=product.id, description=product.name, quantity=qty,
            unit_cost=cost, line_total=quantize_amount(qty * cost),
        ))
        stock_line_total += quantize_amount(qty * cost)
        inventory = StoreInventory.query.filter_by(store_id=store_id, product_id=product.id).one_or_none()
        if inventory is None:
            inventory = StoreInventory(site_id=site_id, store_id=store_id, product_id=product.id, stock_quantity=0)
            db.session.add(inventory)
            db.session.flush()
        before = int(inventory.stock_quantity or 0)
        product.purchase_price = cost
        inventory.stock_quantity = before + qty
        record_inventory_movement(
            product, transaction_type="manual_in", quantity_before=before,
            quantity_after=inventory.stock_quantity, source_type="supplier_invoice",
            source_id=invoice.id, source_reference=f"Alış Faturası {invoice_no}",
            note=supplier.name,
        )
    if normalized_lines and quantize_amount(stock_line_total) != net:
        raise FinanceConfigurationError(
            f"Ürün satırları toplamı ({quantize_amount(stock_line_total)}) ile fatura net tutarı ({net}) uyuşmuyor."
        )
    return invoice


def _post_personnel(record):
    category_code = "CURRENT" if record.record_type == "advance" else "MANUAL_OUT"
    category = FinanceCategory.query.filter_by(site_id=record.site_id, code=category_code).one()
    movement = create_manual_movement(
        site_id=record.site_id, store_id=record.store_id, account_id=record.account_id,
        category_id=category.id, direction="out", amount=record.amount,
        occurred_at=datetime.combine(record.occurred_on, time(hour=12)),
        description=f"{record.personnel_name} · {record.description}",
        is_overhead=record.record_type == "store_expense",
    )
    record.movement_id = movement.id
    record.status = "approved"
    record.decided_at = datetime.utcnow()
    return movement


def create_personnel_record(*, site_id, store_id, personnel_name, record_type, account_id,
                            amount, occurred_on, description, config):
    ensure_finance_period_open(site_id, store_id, occurred_on)
    account = FinanceAccount.query.filter_by(
        id=account_id, site_id=site_id, store_id=store_id, is_active=True
    ).one_or_none()
    if account is None:
        raise FinanceConfigurationError("Geçerli bir finans hesabı seçmelisiniz.")
    if record_type not in {"advance", "store_expense"}:
        raise FinanceConfigurationError("Personel işlem türü geçerli değil.")
    amount = _money(amount)
    if amount <= 0 or not str(personnel_name or "").strip() or not str(description or "").strip():
        raise FinanceConfigurationError("Personel, tutar ve açıklama zorunludur.")
    record = PersonnelFinanceRecord(
        site_id=site_id, store_id=store_id, personnel_name=str(personnel_name).strip(),
        record_type=record_type, account_id=account_id, amount=amount,
        occurred_on=occurred_on, description=str(description).strip(),
        remaining_amount=amount if record_type == "advance" else Decimal("0.00"),
        requested_by_user_id=_user_id(),
    )
    db.session.add(record)
    db.session.flush()
    if amount > _approval_limit(config):
        _queue_approval("personnel", record, f"Personel işlemi: {record.personnel_name}")
    else:
        _post_personnel(record)
    return record


def settle_personnel_advance(*, record, amount, settlement_type, account_id, description=None):
    if record.record_type != "advance" or record.status != "approved":
        raise FinanceConfigurationError("Yalnız onaylanmış personel avansı mahsuplaştırılabilir.")
    amount = _money(amount)
    if amount <= 0 or amount > record.remaining_amount:
        raise FinanceConfigurationError("Mahsup tutarı kalan avansı aşamaz.")
    if settlement_type not in {"cash_return", "expense_offset"}:
        raise FinanceConfigurationError("Mahsup türü geçerli değil.")
    account = FinanceAccount.query.filter_by(
        id=account_id, site_id=record.site_id, store_id=record.store_id, is_active=True
    ).one_or_none()
    if account is None:
        raise FinanceConfigurationError("Finans hesabı bulunamadı.")
    current_category = FinanceCategory.query.filter_by(site_id=record.site_id, code="CURRENT").one()
    cash_movement = create_manual_movement(
        site_id=record.site_id, store_id=record.store_id, account_id=account.id,
        category_id=current_category.id, direction="in", amount=amount,
        occurred_at=datetime.utcnow(),
        description=f"{record.personnel_name} avans mahsubu · {description or settlement_type}",
        is_overhead=False,
    )
    expense_movement = None
    if settlement_type == "expense_offset":
        expense_category = FinanceCategory.query.filter_by(site_id=record.site_id, code="MANUAL_OUT").one()
        expense_movement = create_manual_movement(
            site_id=record.site_id, store_id=record.store_id, account_id=account.id,
            category_id=expense_category.id, direction="out", amount=amount,
            occurred_at=datetime.utcnow(),
            description=f"{record.personnel_name} belge karşılığı avans gideri · {description or '-'}",
            is_overhead=True,
        )
    settlement = PersonnelAdvanceSettlement(
        record_id=record.id, amount=amount, settlement_type=settlement_type,
        finance_account_id=account.id, cash_movement_id=cash_movement.id,
        expense_movement_id=expense_movement.id if expense_movement else None,
        description=str(description or "").strip() or None, created_by_user_id=_user_id(),
    )
    record.remaining_amount = quantize_amount(record.remaining_amount - amount)
    db.session.add(settlement)
    return settlement


def decide_approval(approval, *, approve, note=None):
    if approval.status != "pending":
        raise FinanceConfigurationError("Bu talep daha önce sonuçlandırılmış.")
    entity = (
        db.session.get(ExpenseVoucher, approval.entity_id)
        if approval.entity_type == "expense"
        else db.session.get(PersonnelFinanceRecord, approval.entity_id)
    )
    if entity is None or entity.site_id != approval.site_id or entity.store_id != approval.store_id:
        raise FinanceConfigurationError("Onay kaydının bağlı işlemi bulunamadı.")
    approval.status = "approved" if approve else "rejected"
    approval.decided_by_user_id = _user_id()
    approval.decision_note = str(note or "").strip() or None
    approval.decided_at = datetime.utcnow()
    entity.decided_by_user_id = approval.decided_by_user_id
    entity.decision_note = approval.decision_note
    entity.decided_at = approval.decided_at
    if approve:
        _post_expense(entity) if approval.entity_type == "expense" else _post_personnel(entity)
    else:
        entity.status = "rejected"
    return entity
