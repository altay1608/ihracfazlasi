from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Category, PaymentMethod, Product, RetailMultiplier, Return, ReturnReason, Sale, SaleItem, Variant
from app.modules.admin.forms import (
    CategoryForm,
    PaymentMethodForm,
    RetailMultiplierForm,
    ReturnReasonForm,
    VariantForm,
)
from app.services.reference_data import ensure_reference_data
from app.utils import is_ajax_request, is_modal_request


bp = Blueprint("admin", __name__, url_prefix="/admin")

TAB_CONFIG = {
    "categories": {
        "label": "Kategoriler",
        "model": Category,
        "form_class": CategoryForm,
        "title_add": "Yeni Kategori",
        "title_edit": "Kategori Düzenle",
    },
    "variants": {
        "label": "Bedenler",
        "model": Variant,
        "form_class": VariantForm,
        "title_add": "Yeni Beden / Varyant",
        "title_edit": "Beden / Varyant Düzenle",
    },
    "payment_methods": {
        "label": "Ödeme Yöntemleri",
        "model": PaymentMethod,
        "form_class": PaymentMethodForm,
        "title_add": "Yeni Ödeme Yöntemi",
        "title_edit": "Ödeme Yöntemi Düzenle",
    },
    "return_reasons": {
        "label": "İade Nedenleri",
        "model": ReturnReason,
        "form_class": ReturnReasonForm,
        "title_add": "Yeni İade Nedeni",
        "title_edit": "İade Nedeni Düzenle",
    },
    "retail_multipliers": {
        "label": "Perakende Çarpan Tanımları",
        "model": RetailMultiplier,
        "form_class": RetailMultiplierForm,
        "title_add": "Yeni Perakende Çarpanı",
        "title_edit": "Perakende Çarpanı Düzenle",
    },
}


def get_active_tab():
    tab = request.args.get("tab", "categories")
    return tab if tab in TAB_CONFIG else "categories"


def get_admin_context(active_tab=None):
    ensure_reference_data()
    active_tab = active_tab or get_active_tab()
    return {
        "active_tab": active_tab,
        "tabs": {
            "categories": Category.query.order_by(Category.name.asc()).all(),
            "variants": Variant.query.order_by(Variant.name.asc()).all(),
            "payment_methods": PaymentMethod.query.order_by(PaymentMethod.name.asc()).all(),
            "return_reasons": ReturnReason.query.order_by(ReturnReason.name.asc()).all(),
            "retail_multipliers": RetailMultiplier.query.order_by(RetailMultiplier.multiplier.asc(), RetailMultiplier.name.asc()).all(),
        },
        "tab_config": TAB_CONFIG,
    }


def render_admin_form(entity, form, page_title, record=None, status_code=200):
    template_name = "admin/_form_modal.html" if is_modal_request() else "admin/form.html"
    return (
        render_template(
            template_name,
            entity=entity,
            page_title=page_title,
            form=form,
            record=record,
            active_tab=request.args.get("tab", entity),
            tab_config=TAB_CONFIG,
        ),
        status_code,
    )


@bp.route("/")
def index():
    context = get_admin_context()
    if request.args.get("partial") == "content":
        return render_template("admin/_content.html", **context)
    return render_template("admin/index.html", **context)


@bp.route("/<string:entity>/create", methods=["GET", "POST"])
def create(entity):
    config = TAB_CONFIG.get(entity)
    if not config:
        return ("", 404)

    ensure_reference_data()
    form = config["form_class"]()
    if request.method == "GET" and is_modal_request():
        html, _ = render_admin_form(entity, form, config["title_add"])
        return html
    if form.validate_on_submit():
        record = config["model"]()
        assign_form_data(record, form)
        normalize_default_flags(entity, record)
        db.session.add(record)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            form.name.errors.append("Bu kayıt zaten mevcut.")
        else:
            if is_ajax_request():
                if is_modal_request():
                    return jsonify(
                        {
                            "success": True,
                            "message": "Kayıt kaydedildi.",
                            "refresh_target": "#admin-tabs-content",
                            "refresh_url": _admin_refresh_url(entity),
                        }
                    )
                return jsonify(
                    {
                        "success": True,
                        "message": "Kayıt kaydedildi.",
                        "redirect_url": url_for("admin.index", tab=entity),
                        "persist_message_after_redirect": True,
                    }
                )
    if is_ajax_request():
        html, status_code = render_admin_form(
            entity,
            form,
            config["title_add"],
            status_code=400 if form.errors else 200,
        )
        return jsonify({"success": False, "html": html}), status_code
    return render_admin_form(entity, form, config["title_add"])


@bp.route("/<string:entity>/<int:record_id>/edit", methods=["GET", "POST"])
def edit(entity, record_id):
    config = TAB_CONFIG.get(entity)
    if not config:
        return ("", 404)

    ensure_reference_data()
    record = config["model"].query.get_or_404(record_id)
    form = config["form_class"](obj=record)
    if request.method == "GET" and is_modal_request():
        html, _ = render_admin_form(entity, form, config["title_edit"], record=record)
        return html
    if form.validate_on_submit():
        original_name = getattr(record, "name", None)
        assign_form_data(record, form)
        normalize_default_flags(entity, record)
        try:
            sync_dependent_products(entity, original_name, record.name)
            sync_dependent_records(entity, original_name, record.name)
            db.session.commit()
        except Exception:
            db.session.rollback()
            form.name.errors.append("Bu kayıt güncellenemedi veya aynı isimde kayıt var.")
        else:
            if is_ajax_request():
                if is_modal_request():
                    return jsonify(
                        {
                            "success": True,
                            "message": "Kayıt güncellendi.",
                            "refresh_target": "#admin-tabs-content",
                            "refresh_url": _admin_refresh_url(entity),
                        }
                    )
                return jsonify(
                    {
                        "success": True,
                        "message": "Kayıt güncellendi.",
                        "redirect_url": url_for("admin.index", tab=entity),
                        "persist_message_after_redirect": True,
                    }
                )
    if is_ajax_request():
        html, status_code = render_admin_form(
            entity,
            form,
            config["title_edit"],
            record=record,
            status_code=400 if form.errors else 200,
        )
        return jsonify({"success": False, "html": html}), status_code
    return render_admin_form(entity, form, config["title_edit"], record=record)


@bp.route("/<string:entity>/<int:record_id>/delete", methods=["POST"])
def delete(entity, record_id):
    config = TAB_CONFIG.get(entity)
    if not config:
        if is_ajax_request():
            return jsonify({"success": False, "message": "Geçersiz kayıt türü."}), 404
        flash("Geçersiz kayıt türü.", "error")
        return redirect(url_for("admin.index", tab=get_active_tab()))

    ensure_reference_data()
    record = config["model"].query.get_or_404(record_id)
    message = handle_delete_rule(entity, record)
    if message is True:
        db.session.delete(record)
        db.session.commit()
        if is_ajax_request():
            return jsonify(
                {
                    "success": True,
                    "message": "Kayıt silindi.",
                    "refresh_target": "#admin-tabs-content",
                    "refresh_url": _admin_refresh_url(entity),
                }
            )
        flash("Kayıt silindi.", "success")
        return redirect(url_for("admin.index", tab=entity))
    if isinstance(message, tuple):
        success_message, post_action = message
        post_action()
        db.session.delete(record)
        db.session.commit()
        if is_ajax_request():
            return jsonify(
                {
                    "success": True,
                    "message": success_message,
                    "refresh_target": "#admin-tabs-content",
                    "refresh_url": _admin_refresh_url(entity),
                }
            )
        flash(success_message, "success")
        return redirect(url_for("admin.index", tab=entity))
    if is_ajax_request():
        return jsonify({"success": False, "message": message}), 400
    flash(message, "error")
    return redirect(url_for("admin.index", tab=entity))


@bp.route("/<string:entity>/<int:record_id>/toggle", methods=["POST"])
def toggle_record(entity, record_id):
    ensure_reference_data()
    config = TAB_CONFIG.get(entity)
    if not config:
        if is_ajax_request():
            return jsonify({"success": False, "message": "Geçersiz kayıt türü."}), 404
        flash("Geçersiz kayıt türü.", "error")
        return redirect(url_for("admin.index", tab=get_active_tab()))

    record = config["model"].query.get_or_404(record_id)
    if not hasattr(record, "is_active"):
        if is_ajax_request():
            return jsonify({"success": False, "message": "Bu kayıt türünde aktif/pasif desteği yok."}), 400
        flash("Bu kayıt türünde aktif/pasif desteği yok.", "error")
        return redirect(url_for("admin.index", tab=entity))

    record.is_active = not record.is_active
    if entity == "retail_multipliers" and not record.is_active and record.is_default:
        next_default = RetailMultiplier.query.filter(
            RetailMultiplier.id != record.id,
            RetailMultiplier.is_active.is_(True),
        ).order_by(RetailMultiplier.multiplier.asc(), RetailMultiplier.name.asc()).first()
        if next_default:
            next_default.is_default = True
        record.is_default = False
    db.session.commit()
    message = f"{record.name} {'aktif' if record.is_active else 'pasif'} yapıldı."
    if is_ajax_request():
        return jsonify(
            {
                "success": True,
                "message": message,
                "refresh_target": "#admin-tabs-content",
                "refresh_url": _admin_refresh_url(entity),
            }
        )
    flash(message, "success")
    return redirect(url_for("admin.index", tab=entity))


@bp.route("/payment_methods/<int:record_id>/toggle", methods=["POST"])
def toggle_payment_method(record_id):
    return toggle_record("payment_methods", record_id)


def assign_form_data(record, form):
    record.name = form.name.data.strip()
    if hasattr(record, "description"):
        record.description = (form.description.data or "").strip() or None
    if hasattr(record, "critical_stock_level"):
        record.critical_stock_level = form.critical_stock_level.data
    if hasattr(record, "is_active"):
        record.is_active = bool(form.is_active.data)
    if hasattr(record, "multiplier"):
        record.multiplier = form.multiplier.data
    if hasattr(record, "is_default"):
        record.is_default = bool(form.is_default.data)


def normalize_default_flags(entity, record):
    if entity != "retail_multipliers":
        return
    if record.is_default:
        RetailMultiplier.query.filter(RetailMultiplier.id != record.id).update({"is_default": False})
    elif not RetailMultiplier.query.filter(RetailMultiplier.id != record.id, RetailMultiplier.is_default.is_(True)).first():
        record.is_default = True


def sync_dependent_products(entity, original_name, new_name):
    if not original_name or original_name == new_name:
        return
    if entity == "categories":
        Product.query.filter_by(category=original_name).update({"category": new_name})
    elif entity == "variants":
        Product.query.filter_by(variant=original_name).update({"variant": new_name})


def sync_dependent_records(entity, original_name, new_name):
    if not original_name or original_name == new_name:
        return
    if entity == "payment_methods":
        Sale.query.filter_by(payment_method=original_name).update({"payment_method": new_name})
    elif entity == "return_reasons":
        Return.query.filter_by(reason=original_name).update({"reason": new_name})


def handle_delete_rule(entity, record):
    if entity == "categories":
        products = Product.query.filter_by(category=record.name).all()
        sold_exists = (
            db.session.query(SaleItem.id)
            .join(Product, Product.id == SaleItem.product_id)
            .filter(Product.category == record.name)
            .first()
            is not None
        )
        if sold_exists:
            return "Bu kategoriye ait satışı olan ürünler bulunmaktadır, kategori silinemez."
        if products:
            fallback = Category.query.filter_by(name="Diğer").first()

            def reassign():
                for product in products:
                    product.category = fallback.name if fallback else "Diğer"

            return ("Kategori silindi. Ürünler 'Diğer' kategorisine taşındı.", reassign)
        return True

    if entity == "variants":
        products = Product.query.filter_by(variant=record.name).all()
        sold_exists = (
            db.session.query(SaleItem.id)
            .join(Product, Product.id == SaleItem.product_id)
            .filter(Product.variant == record.name)
            .first()
            is not None
        )
        if sold_exists:
            return "Bu varyantı kullanan satışı olan ürünler bulunduğu için silinemez."
        if products:
            def clear_variant():
                for product in products:
                    product.variant = None

            return ("Varyant silindi. Bağlı ürünlerin varyant alanı temizlendi.", clear_variant)
        return True

    if entity == "payment_methods":
        if Sale.query.filter_by(payment_method=record.name).first():
            return "Bu ödeme yöntemi satışlarda kullanıldığı için silinemez."
        return True

    if entity == "return_reasons":
        if Return.query.filter_by(reason=record.name).first():
            return "Bu iade nedeni mevcut kayıtlarda kullanıldığı için silinemez."
        return True

    if entity == "retail_multipliers":
        if Product.query.filter_by(retail_multiplier_id=record.id).first():
            return "Bu perakende çarpanı ürünlerde kullanıldığı için silinemez."
        return True

    return True


def _admin_refresh_url(tab):
    return f"/admin/?partial=content&tab={tab}"
