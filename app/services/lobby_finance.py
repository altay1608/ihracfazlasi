"""Read-only, store-scoped monthly money narrative for the lobby."""
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func
from sqlalchemy.orm import aliased

from app.extensions import db
from app.models.finance import FinanceAccount, FinanceCategory, FinanceMovement, CurrentAccount
from app.utils import istanbul_day_start_utc, utc_to_istanbul


def build_lobby_finance(site_id, store_id, today):
    original = aliased(FinanceMovement)
    effective_type = func.coalesce(original.movement_type, FinanceMovement.movement_type)
    scope = (
        FinanceMovement.site_id == site_id,
        FinanceMovement.store_id == store_id,
        FinanceMovement.occurred_at >= istanbul_day_start_utc(today.replace(day=1)),
        FinanceMovement.occurred_at < istanbul_day_start_utc(today + timedelta(days=1)),
    )
    signed = case((FinanceMovement.direction == "in", FinanceMovement.amount), else_=-FinanceMovement.amount)
    # Group corrections with the original direction, so a reversed expense cancels it.
    direction = func.coalesce(original.direction, FinanceMovement.direction)
    base = db.session.query(FinanceMovement).outerjoin(original, and_(
        original.id == FinanceMovement.reversal_of_id,
        original.site_id == site_id, original.store_id == store_id,
    )).outerjoin(FinanceAccount, and_(
        FinanceAccount.id == FinanceMovement.account_id,
        FinanceAccount.site_id == site_id, FinanceAccount.store_id == store_id,
    )).outerjoin(FinanceCategory, and_(
        FinanceCategory.id == FinanceMovement.category_id, FinanceCategory.site_id == site_id,
    )).outerjoin(CurrentAccount, and_(
        CurrentAccount.id == FinanceMovement.current_account_id, CurrentAccount.site_id == site_id,
    )).filter(*scope)
    grouped = base.with_entities(
        effective_type.label("kind"), direction.label("direction"),
        FinanceMovement.is_overhead.label("overhead"),
        FinanceAccount.name.label("account"), FinanceCategory.name.label("category"),
        CurrentAccount.name.label("person"), func.sum(signed).label("amount"),
    ).group_by(effective_type, direction, FinanceMovement.is_overhead, FinanceAccount.name, FinanceCategory.name, CurrentAccount.name).all()
    labels = {
        "supplier_return": "Toptancıdan ürün iade bedeli",
        "sale": "Satış hareketi", "exchange_sale": "Değişim satışı",
        "return": "İade", "manual": "Manuel gelir / gider",
        "pos_commission": "Banka komisyonu", "transfer": "Hesaplar arası aktarım",
        "current_settlement": "Cari tahsilat / borç ödemesi",
        "obligation_payment": "Dönemsel borç ödemesi",
        "pos_reconciliation": "Kart tutarının bankaya aktarımı",
        "opening_balance": "Açılış bakiyesi", "opening_adjustment": "Bakiye düzeltmesi",
    }
    rows = []
    for row in grouped:
        amount = Decimal(row.amount or 0)
        if not amount:
            continue
        title = labels.get(row.kind, "Finans hareketi")
        if row.kind == "manual":
            title = "Manuel para girişi" if row.direction == "in" else ("Genel gider" if row.overhead else "Diğer para çıkışı")
        elif row.kind == "current_settlement":
            title = "Cari tahsilat" if row.direction == "in" else "Cari borç ödemesi"
        rows.append(dict(title=title, account=row.account or "Hesap", category=row.category,
                         person=row.person, amount=abs(amount), incoming=amount > 0))
    rows.sort(key=lambda row: (row["title"], row["account"], row["category"] or "", row["person"] or ""))
    recent = base.with_entities(
        FinanceMovement.id, FinanceMovement.occurred_at, FinanceMovement.description,
        FinanceMovement.amount, FinanceMovement.direction,
        FinanceAccount.name.label("account"), CurrentAccount.name.label("person"),
    ).order_by(FinanceMovement.occurred_at.desc(), FinanceMovement.id.desc()).limit(5).all()
    return {"rows": rows, "recent": [dict(
        date=utc_to_istanbul(row.occurred_at).strftime("%d.%m.%Y %H:%M"),
        description=row.description or "Finans hareketi", account=row.account or "Hesap",
        person=row.person, amount=row.amount, incoming=row.direction == "in",
    ) for row in recent]}
