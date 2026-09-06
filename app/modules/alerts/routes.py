from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Category, Product, StoreInventory
from app.services.reporting import attach_stock_thresholds


bp = Blueprint("alerts", __name__, url_prefix="/alerts")


def _parse_threshold(raw_value):
    value = str(raw_value or "").strip()
    if value == "":
        return None
    parsed = int(value)
    if parsed < 0:
        raise ValueError
    return parsed


@bp.route("/")
def index():
    fallback_threshold = current_app.config["LOW_STOCK_THRESHOLD"]
    categories = Category.query.order_by(Category.name.asc()).all()
    products = (
        Product.query.join(StoreInventory, StoreInventory.product_id == Product.id)
        .order_by(StoreInventory.stock_quantity.asc(), Product.name.asc())
        .all()
    )
    attach_stock_thresholds(products, fallback_threshold)
    for product in products:
        target_stock = max(int(product.effective_low_stock_threshold or 0) * 2, int(product.effective_low_stock_threshold or 0))
        product.recommended_order_quantity = max(target_stock - int(product.stock_quantity or 0), 0)
    low_products_count = len(
        [product for product in products if product.stock_quantity <= product.effective_low_stock_threshold]
    )
    return render_template(
        "alerts/index.html",
        products=products,
        categories=categories,
        low_products_count=low_products_count,
        threshold=fallback_threshold,
    )


@bp.route("/categories/<int:category_id>/threshold", methods=["POST"])
def update_category_threshold(category_id):
    category = Category.query.get_or_404(category_id)
    try:
        category.critical_stock_level = _parse_threshold(request.form.get("critical_stock_level"))
    except ValueError:
        flash("Kategori KSS değeri 0 veya daha büyük olmalı.", "error")
    else:
        db.session.commit()
        flash(f"{category.name} için kategori KSS güncellendi.", "success")
    return redirect(url_for("alerts.index"))


@bp.route("/products/<int:product_id>/threshold", methods=["POST"])
def update_product_threshold(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        product.critical_stock_level = _parse_threshold(request.form.get("critical_stock_level"))
    except ValueError:
        flash("Ürün KSS değeri 0 veya daha büyük olmalı.", "error")
    else:
        db.session.commit()
        if product.critical_stock_level is None:
            flash(f"{product.name} için ürün bazlı KSS temizlendi.", "success")
        else:
            flash(f"{product.name} için ürün bazlı KSS güncellendi.", "success")
    return redirect(url_for("alerts.index"))
