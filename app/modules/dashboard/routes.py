from datetime import timedelta

from flask import Blueprint, render_template

from app.services.access_control import has_permission
from app.services.reporting import (
    ZERO,
    get_daily_turnover,
    get_dashboard_metrics,
    get_top_products,
)
from app.utils import now_in_istanbul


bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    today = now_in_istanbul().date()
    month_start = today.replace(day=1)
    show_finance = has_permission("dashboard.column.finance")
    show_trend = has_permission("dashboard.column.sales_trend")
    metrics = get_dashboard_metrics(today) if show_finance or show_trend else {}
    turnover = get_daily_turnover(min(month_start, today - timedelta(days=6)), today) if show_finance or show_trend else []
    chart_data = [{"label": row["date"].strftime("%d.%m"), "value": float(row["revenue"])} for row in turnover[-7:]]
    top_products = get_top_products() if show_trend else []
    month_total = sum((row["revenue"] for row in turnover if row["date"] >= month_start), ZERO)
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
    )
