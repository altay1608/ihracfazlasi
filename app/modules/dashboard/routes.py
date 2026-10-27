from datetime import timedelta

from flask import Blueprint, render_template, request

from app.services.access_control import has_permission, permission_required
from app.services.store_tools import due_agenda, slow_stock, customer_history
from app.services.lobby_finance import build_lobby_finance
from app.services.finance_reporting import actual_expenses_between, build_operating_profit_summary
from app.services.identity_access import get_active_site_id, get_active_store_id
from app.services.reporting import (
    ZERO,
    get_daily_turnover,
    get_dashboard_metrics,
    get_top_products,
    get_profit_report,
)
from app.utils import now_in_istanbul, quantize_amount


bp = Blueprint("dashboard", __name__)


@bp.get("/payment-agenda")
@permission_required("finance.accounts.manage")
def payment_agenda():
    today = now_in_istanbul().date()
    return render_template("dashboard/payment_agenda.html", today=today,
        rows=due_agenda(get_active_site_id(), get_active_store_id(), today))


@bp.get("/slow-stock")
@permission_required("products.access")
def slow_stock_page():
    days = request.args.get("days", 60, type=int)
    days = days if days in (30, 60, 90, 180) else 60
    return render_template("dashboard/slow_stock.html", days=days,
        rows=slow_stock(get_active_site_id(), get_active_store_id(), now_in_istanbul().date(), days))


@bp.get("/customer-history")
@permission_required("sales.access")
@permission_required("sales.customer.view")
def customer_history_page():
    phone = request.args.get("phone", "").strip()[:40]
    return render_template("dashboard/customer_history.html", phone=phone,
        **customer_history(get_active_site_id(), get_active_store_id(), phone))


@bp.route("/")
def index():
    today = now_in_istanbul().date()
    month_start = today.replace(day=1)
    show_finance = has_permission("dashboard.column.finance")
    show_trend = has_permission("dashboard.column.sales_trend")
    metrics = get_dashboard_metrics(today) if show_finance or show_trend else {}
    if show_finance:
        operating = build_operating_profit_summary(get_profit_report(today, today), ZERO)
        expenses = actual_expenses_between(get_active_site_id(), get_active_store_id(), today, today)
        metrics["net_profit"] = quantize_amount(operating["gross_profit"] - expenses["total"])
    turnover = get_daily_turnover(min(month_start, today - timedelta(days=6)), today) if show_finance or show_trend else []
    chart_data = [{"label": row["date"].strftime("%d.%m"), "value": float(row["revenue"])} for row in turnover[-7:]]
    top_products = get_top_products() if show_trend else []
    month_total = sum((row["revenue"] for row in turnover if row["date"] >= month_start), ZERO)
    finance_summary = build_lobby_finance(get_active_site_id(), get_active_store_id(), today) if show_finance and has_permission("finance.ledger.view") else None
    if turnover:
        # Keep the headline, graph and daily list on the same turnover basis.
        metrics["revenue"] = turnover[-1]["revenue"]
    return render_template(
        "dashboard/index.html",
        metrics=metrics,
        chart_data=chart_data,
        top_products=top_products,
        recent_turnover=list(reversed(turnover[-5:])),
        month_total=month_total,
        month_start=month_start,
        today=today,
        finance_summary=finance_summary,
    )
