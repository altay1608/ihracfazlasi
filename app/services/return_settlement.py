"""Explicit return payment and customer-verified debt offsets, one transaction."""
import re
from decimal import Decimal
from sqlalchemy import or_, func
from app.extensions import db
from app.models import Sale, CurrentAccount, CurrentEntry, ReturnSettlement
from app.services.finance import (credit_sale_remaining, _require_activation, _mapped_account,
    _append_movement, _category, _lock_finance_account, get_account_balance, ensure_finance_period_open)
from app.utils import quantize_amount

METHODS = ('Nakit', 'Kredi Kartı', 'Havale/EFT')


def phone(value):
    digits = re.sub(r'\D', '', value or '')
    if len(digits) == 12 and digits.startswith('90'):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    return digits if len(digits) == 10 else ''


def identity(sale):
    return {p for p in (phone(sale.customer_mobile), phone(sale.customer_phone)) if p}


def sale_credit_offsets(sale):
    if not getattr(sale, 'id', None):
        return Decimal('0.00')
    return quantize_amount(db.session.query(func.coalesce(func.sum(ReturnSettlement.credit_amount), 0)).filter_by(
        site_id=sale.site_id, store_id=sale.store_id, credit_sale_id=sale.id).scalar())


def resolve_debt(sale, key, lock=False):
    try:
        kind, raw = key.split(':')
        target_id = int(raw)
    except (ValueError, AttributeError):
        raise ValueError('Geçerli bir müşteri borcu seçin.')
    if kind == 'sale':
        query = Sale.query.filter_by(id=target_id, site_id=sale.site_id, store_id=sale.store_id)
        target = (query.populate_existing().with_for_update() if lock else query).first()
        if not target or target.order_status == 'CANCELLED' or (target.id != sale.id and not identity(sale).intersection(identity(target))):
            raise ValueError('Seçilen borç bu müşteri ve mağazayla eşleşmiyor.')
        return target, credit_sale_remaining(target)
    if kind == 'entry':
        query = CurrentEntry.query.filter_by(id=target_id, site_id=sale.site_id, store_id=sale.store_id, entry_type='receivable')
        target = (query.populate_existing().with_for_update() if lock else query).first()
        account = db.session.get(CurrentAccount, target.current_account_id) if target else None
        if not account or account.site_id != sale.site_id or account.account_category != 'customer' or not account.is_active or phone(account.phone) not in identity(sale):
            raise ValueError('Cari müşteri telefon bilgisi satışla eşleşmiyor.')
        return target, target.remaining_amount
    raise ValueError('Geçerli bir borç türü seçin.')


def debt_choices(sale):
    if not sale:
        return []
    rows = []
    for target in Sale.query.filter(Sale.site_id == sale.site_id, Sale.store_id == sale.store_id,
            Sale.order_status != 'CANCELLED', or_(Sale.payment_method == 'Veresiye', Sale.payments.any(payment_method='Veresiye'))).all():
        if target.id == sale.id or identity(sale).intersection(identity(target)):
            amount = credit_sale_remaining(target)
            if amount > 0:
                rows.append((f'sale:{target.id}', f'Veresiye satış #{target.document_no} — {amount:.2f} TL'))
    if identity(sale):
        for target, account in db.session.query(CurrentEntry, CurrentAccount).join(CurrentAccount, CurrentEntry.current_account_id == CurrentAccount.id).filter(
            CurrentEntry.site_id == sale.site_id, CurrentEntry.store_id == sale.store_id,
            CurrentEntry.entry_type == 'receivable', CurrentEntry.remaining_amount > 0,
            CurrentAccount.site_id == sale.site_id, CurrentAccount.account_category == 'customer', CurrentAccount.is_active.is_(True)).all():
            if phone(account.phone) in identity(sale):
                rows.append((f'entry:{target.id}', f'Cari #{target.id} / {account.name} — {target.remaining_amount:.2f} TL'))
    return rows


def settlement_plan(sale, returned, replacement, debt_key, method, lock=False):
    net = quantize_amount(returned - replacement)
    offset = Decimal('0.00')
    target = None
    if debt_key:
        if net <= 0:
            raise ValueError('Borçtan düşme yalnız müşteriye iade edilecek fark varsa seçilebilir.')
        target, remaining = resolve_debt(sale, debt_key, lock)
        if remaining <= 0:
            raise ValueError('Seçilen borç kapanmış. Başka borç veya ödeme yöntemi seçin.')
        offset = min(net, remaining)
    cash = quantize_amount(net - offset)
    if method not in METHODS and cash != 0:
        raise ValueError('Ödenecek veya tahsil edilecek fark için ödeme yöntemi seçin.')
    return dict(returned=str(returned), replacement=str(replacement), net=str(net), credit=str(offset), cash=str(cash),
                debt_key=debt_key or '', method=method if method in METHODS else 'Fark Yok'), target


def post_settlement(record, plan, target):
    existing = ReturnSettlement.query.filter_by(return_id=record.id).first()
    if existing:
        return existing
    _require_activation(record.site_id, record.store_id)
    ensure_finance_period_open(record.site_id, record.store_id, record.return_date)
    credit, cash = Decimal(plan['credit']), Decimal(plan['cash'])
    returned, replacement = Decimal(plan['returned']), Decimal(plan['replacement'])
    row = ReturnSettlement(return_id=record.id, site_id=record.site_id, store_id=record.store_id,
        credit_sale_id=target.id if isinstance(target, Sale) else None,
        current_entry_id=target.id if isinstance(target, CurrentEntry) else None,
        credit_amount=credit, cash_amount=cash, payment_method=plan['method'])
    # Post full return/replacement totals for reports; only the net moves cash.
    account = _lock_finance_account(_mapped_account(record.site_id, record.store_id,
        plan['method'] if plan['method'] in METHODS else 'Nakit'))
    if cash > 0 and get_account_balance(account) < cash:
        raise ValueError('Seçilen ödeme hesabında iade farkını karşılayacak bakiye yok.')
    def movement(account, direction, amount, kind, suffix):
        if amount <= 0:
            return
        _append_movement(site_id=record.site_id, store_id=record.store_id, account=account,
            category=_category(record.site_id, 'RETURN' if kind == 'return' else 'CURRENT' if kind == 'current_settlement' else 'EXCHANGE_REPLACEMENT'),
            direction=direction, amount=amount, occurred_at=record.return_date, movement_type=kind,
            description=f'İade/değişim #{record.document_no} · {plan["method"]} · borçtan düşülen {credit}',
            source_type='return', source_id=record.id, source_key=f'return:{record.id}:settlement:{suffix}',
            pair_key=f'return:{record.id}:settlement')
    movement(account, 'out', returned - credit, 'return', 'refund')
    movement(account, 'in', replacement, 'exchange_sale', 'replacement')
    if credit:
        credit_account = _lock_finance_account(_mapped_account(record.site_id, record.store_id, 'Veresiye'))
        if isinstance(target, CurrentEntry):
            # Manual receivables are not originally booked to the CREDIT ledger.
            movement(credit_account, 'in', credit, 'current_settlement', 'manual-offset')
            target.remaining_amount = quantize_amount(target.remaining_amount - credit)
            target.status = 'closed' if target.remaining_amount == 0 else 'partial'
        movement(credit_account, 'out', credit, 'return', 'credit-offset')
    db.session.add(row)
    db.session.flush()
    return row
