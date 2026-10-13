"""Read-only store planning and customer views; no automatic money movements."""
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import lazyload, selectinload
from app.extensions import db
from app.models import Product, Sale, SaleItem, StoreInventory, Return
from app.models.finance import CurrentEntry, CurrentAccount, ShortTermObligation, PosReconciliation
from app.services.finance import credit_sale_summary
from app.utils import istanbul_day_start_utc, utc_to_istanbul


def due_agenda(site_id, store_id, today):
    end = today + timedelta(days=7)
    rows = []
    credits = Sale.query.options(lazyload("*"), selectinload(Sale.payments), selectinload(Sale.credit_collections)).filter(
        Sale.site_id == site_id, Sale.store_id == store_id,
        Sale.order_status.notin_(("CANCELLED", "RETURNED")),
        or_(Sale.payment_method == "Veresiye", Sale.payments.any(payment_method="Veresiye")),
        or_(Sale.payment_due_date <= end, Sale.payment_due_date.is_(None)),
    ).all()
    for sale in credits:
        remaining = credit_sale_summary(sale)["remaining"]
        if remaining > 0:
            rows.append(dict(kind="Müşteriden tahsilat", name=sale.customer_name or sale.customer_mobile or f"Fiş #{sale.document_no}",
                due=sale.payment_due_date, amount=remaining, endpoint="sales.detail", params={"sale_id": sale.id}))
    debts = db.session.query(CurrentEntry, CurrentAccount.name).outerjoin(CurrentAccount, and_(
        CurrentAccount.id == CurrentEntry.current_account_id, CurrentAccount.site_id == site_id,
    )).filter(CurrentEntry.site_id == site_id, CurrentEntry.store_id == store_id,
        CurrentEntry.remaining_amount > 0, or_(CurrentEntry.due_date <= end, CurrentEntry.due_date.is_(None))).all()
    for entry, name in debts:
        rows.append(dict(kind="Cari ödeme" if entry.entry_type == "payable" else "Cari tahsilat", name=name or entry.description,
            due=entry.due_date, amount=entry.remaining_amount, endpoint="finance.current_accounts", params={}))
    for debt in ShortTermObligation.query.filter(
        ShortTermObligation.site_id == site_id, ShortTermObligation.store_id == store_id,
        ShortTermObligation.remaining_amount > 0,
        or_(ShortTermObligation.due_date <= end, ShortTermObligation.due_date.is_(None)),
    ).all():
        rows.append(dict(kind="Dönemsel ödeme", name=debt.title, due=debt.due_date, amount=debt.remaining_amount,
            endpoint="finance.obligations", params={}))
    for pos in PosReconciliation.query.filter(
        PosReconciliation.site_id == site_id, PosReconciliation.store_id == store_id,
        PosReconciliation.status == "pending",
        or_(PosReconciliation.expected_settlement_date <= end, PosReconciliation.expected_settlement_date.is_(None)),
    ).all():
        rows.append(dict(kind="Bankaya beklenen kart ödemesi", name=pos.reference or "POS aktarımı",
            due=pos.expected_settlement_date, amount=pos.net_amount, endpoint="finance.pos_reconciliations", params={}))
    rows.sort(key=lambda row: (row["due"] is None, row["due"] or end, row["kind"], row["name"] or ""))
    return rows


def slow_stock(site_id, store_id, today, days=60):
    last_sale = db.session.query(SaleItem.product_id.label("product_id"), func.max(Sale.sale_date).label("last_sale")).join(
        Sale, Sale.id == SaleItem.sale_id).filter(
        Sale.site_id == site_id, Sale.store_id == store_id, SaleItem.site_id == site_id, SaleItem.store_id == store_id,
        Sale.order_status != "CANCELLED", SaleItem.line_type == "sale",
    ).group_by(SaleItem.product_id).subquery()
    since = func.coalesce(last_sale.c.last_sale, StoreInventory.created_at, Product.created_at)
    results = db.session.query(Product.id, Product.name, Product.variant, Product.product_code,
        Product.purchase_price, StoreInventory.stock_quantity, since.label("since"), last_sale.c.last_sale).join(
        StoreInventory, and_(StoreInventory.product_id == Product.id, StoreInventory.site_id == site_id,
                             StoreInventory.store_id == store_id)).outerjoin(last_sale, last_sale.c.product_id == Product.id).filter(
        Product.site_id == site_id, StoreInventory.stock_quantity > 0,
        since < istanbul_day_start_utc(today - timedelta(days=days)),
    ).order_by(since.asc(), Product.id.asc()).limit(500).all()
    return [dict(id=row.id, name=row.name, variant=row.variant, code=row.product_code,
        quantity=row.stock_quantity, cost=Decimal(row.purchase_price or 0) * row.stock_quantity,
        days=(today - utc_to_istanbul(row.since).date()).days, never_sold=row.last_sale is None) for row in results]


def customer_history(site_id, store_id, phone):
    # Exact phone identity only; never merge unrelated people by name.
    sales = Sale.query.options(lazyload("*"), selectinload(Sale.items), selectinload(Sale.payments),
        selectinload(Sale.credit_collections)).filter(Sale.site_id == site_id, Sale.store_id == store_id,
        or_(Sale.customer_mobile == phone, Sale.customer_phone == phone)).order_by(Sale.sale_date.desc()).all() if phone else []
    sale_ids = [sale.id for sale in sales]
    returns = Return.query.options(lazyload("*")).filter(Return.site_id == site_id, Return.store_id == store_id,
        Return.original_sale_id.in_(sale_ids)).order_by(Return.return_date.desc()).all() if sale_ids else []
    outstanding = sum((credit_sale_summary(sale)["remaining"] for sale in sales
        if sale.order_status not in ("CANCELLED", "RETURNED")), Decimal("0.00"))
    return dict(sales=sales, returns=returns, outstanding=outstanding)
