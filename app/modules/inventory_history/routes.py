from datetime import datetime, time

from flask import Blueprint, render_template, request
from sqlalchemy import or_

from app.models import InventoryTransaction


bp = Blueprint("inventory_history", __name__, url_prefix="/inventory-history")


def parse_date_filter(value, *, end_of_day=False):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    return datetime.combine(parsed, time.max if end_of_day else time.min)


@bp.route("/")
def index():
    search = request.args.get("search", "").strip()
    transaction_code = request.args.get("transaction_code", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    query = InventoryTransaction.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                InventoryTransaction.product_name.ilike(like),
                InventoryTransaction.product_code.ilike(like),
                InventoryTransaction.barcode_values.ilike(like),
                InventoryTransaction.source_reference.ilike(like),
            )
        )
    if transaction_code:
        query = query.filter(InventoryTransaction.transaction_code.ilike(f"%{transaction_code}%"))
    start_at = parse_date_filter(start_date)
    end_at = parse_date_filter(end_date, end_of_day=True)
    if start_at:
        query = query.filter(InventoryTransaction.occurred_at >= start_at)
    if end_at:
        query = query.filter(InventoryTransaction.occurred_at <= end_at)

    transactions = query.order_by(InventoryTransaction.occurred_at.desc(), InventoryTransaction.id.desc()).limit(2000).all()
    total_in = sum(item.quantity_delta for item in transactions if item.quantity_delta > 0)
    total_out = abs(sum(item.quantity_delta for item in transactions if item.quantity_delta < 0))
    return render_template(
        "inventory_history/index.html",
        transactions=transactions,
        summary={
            "total_transactions": len(transactions),
            "total_in": total_in,
            "total_out": total_out,
            "net_quantity": total_in - total_out,
        },
        filters={
            "search": search,
            "transaction_code": transaction_code,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
