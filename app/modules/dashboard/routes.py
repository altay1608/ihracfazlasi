from flask import Blueprint, current_app, render_template

from app.services.reporting import (
    get_dashboard_metrics,
    get_last_7_days_sales,
    get_low_stock_products,
    get_top_products,
)


bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    threshold = current_app.config["LOW_STOCK_THRESHOLD"]
    metrics = get_dashboard_metrics()
    chart_data = get_last_7_days_sales()
    top_products = get_top_products()
    low_stock_products = get_low_stock_products(threshold)
    return render_template(
        "dashboard/index.html",
        metrics=metrics,
        chart_data=chart_data,
        top_products=top_products,
        low_stock_products=low_stock_products,
        threshold=threshold,
    )
