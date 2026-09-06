from datetime import datetime
from decimal import Decimal

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Category, InventoryCount, InventoryCountLine, InventoryCountScan, Product, ProductBarcode
from app.services.inventory_history import record_inventory_movement
from app.services.product_inventory import resolve_unit_barcode
from app.services.reference_data import ensure_reference_data
from app.utils import quantize_amount


bp = Blueprint("inventory_counts", __name__, url_prefix="/inventory-counts")


def resolve_inventory_barcode(raw_barcode):
    return resolve_unit_barcode(raw_barcode)


def build_count_summary(inventory_count):
    positive_quantity = 0
    negative_quantity = 0
    positive_amount = Decimal("0.00")
    negative_amount = Decimal("0.00")

    for line in inventory_count.lines:
        variance_quantity = int(line.counted_quantity or 0) - int(line.system_quantity or 0)
        variance_amount = quantize_amount(Decimal(variance_quantity) * Decimal(str(line.unit_cost or 0)))
        line.variance_quantity = variance_quantity
        line.variance_amount = variance_amount

        if variance_quantity > 0:
            positive_quantity += variance_quantity
            positive_amount += variance_amount
        elif variance_quantity < 0:
            negative_quantity += abs(variance_quantity)
            negative_amount += abs(variance_amount)

    return {
        "positive_quantity": positive_quantity,
        "negative_quantity": negative_quantity,
        "positive_amount": quantize_amount(positive_amount),
        "negative_amount": quantize_amount(negative_amount),
        "net_amount": quantize_amount(positive_amount - negative_amount),
    }


@bp.route("/")
def index():
    counts = InventoryCount.query.order_by(InventoryCount.created_at.desc()).all()
    if request.args.get("partial") == "table":
        return render_template("inventory_counts/_list_section.html", counts=counts)
    return render_template("inventory_counts/index.html", counts=counts)


@bp.route("/create", methods=["GET", "POST"])
def create():
    ensure_reference_data()
    categories = Category.query.order_by(Category.name.asc()).all()

    if request.method == "POST":
        name = (request.form.get("name") or "").strip() or f"Sayım {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        category_filter = (request.form.get("category_filter") or "").strip() or None

        query = Product.query.order_by(Product.category.asc(), Product.name.asc(), Product.variant.asc())
        if category_filter:
            query = query.filter(Product.category == category_filter)
        products = query.all()

        if not products:
            flash("Seçilen filtreye göre sayım listesi oluşturulacak ürün bulunamadı.", "error")
            return render_template(
                "inventory_counts/create.html",
                categories=categories,
                selected_category=category_filter,
                suggested_name=name,
            )

        inventory_count = InventoryCount(name=name, category_filter=category_filter)
        db.session.add(inventory_count)
        db.session.flush()

        for product in products:
            db.session.add(
                InventoryCountLine(
                    inventory_count_id=inventory_count.id,
                    product_id=product.id,
                    system_quantity=product.stock_quantity,
                    counted_quantity=0,
                    unit_cost=product.purchase_price,
                )
            )

        db.session.commit()
        flash(f"{len(products)} ürünlük sayım listesi oluşturuldu.", "success")
        return redirect(url_for("inventory_counts.detail", count_id=inventory_count.id))

    return render_template("inventory_counts/create.html", categories=categories, selected_category="", suggested_name="")


@bp.route("/<int:count_id>")
def detail(count_id):
    inventory_count = InventoryCount.query.get_or_404(count_id)
    summary = build_count_summary(inventory_count)
    return render_template("inventory_counts/detail.html", inventory_count=inventory_count, summary=summary)


@bp.route("/<int:count_id>/delete", methods=["POST"])
def delete(count_id):
    inventory_count = InventoryCount.query.get_or_404(count_id)
    count_name = inventory_count.name

    if inventory_count.status == "approved":
        message = "Onaylanmış sayım kayıtları silinemez."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": message}), 400
        flash(message, "error")
        return redirect(url_for("inventory_counts.index"))

    db.session.delete(inventory_count)
    db.session.commit()
    message = f"{count_name} isimli sayım listesi silindi."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "success": True,
                "message": message,
                "refresh_target": "#inventoryCountsListSection",
                "refresh_url": url_for("inventory_counts.index", partial="table"),
            }
        )

    flash(message, "success")
    return redirect(url_for("inventory_counts.index"))


@bp.route("/<int:count_id>/save", methods=["POST"])
def save(count_id):
    inventory_count = InventoryCount.query.get_or_404(count_id)
    if inventory_count.status == "approved":
        flash("Onaylanmış sayım listesi tekrar düzenlenemez.", "error")
        return redirect(url_for("inventory_counts.detail", count_id=count_id))

    for line in inventory_count.lines:
        line.counted_quantity = len(line.scans)

    db.session.commit()
    flash("Okutulan birim barkodları sayım listesine kaydedildi.", "success")
    return redirect(url_for("inventory_counts.detail", count_id=count_id))


@bp.route("/<int:count_id>/scan", methods=["POST"])
def scan(count_id):
    inventory_count = InventoryCount.query.get_or_404(count_id)
    if inventory_count.status == "approved":
        return jsonify(
            {
                "success": False,
                "error_code": "inventory_count_approved",
                "message": "Onaylanmış sayım listesine okutma yapılamaz.",
            }
        ), 400

    payload = request.get_json(silent=True) or request.form
    raw_barcode = str(payload.get("barcode") or "").strip()
    barcode_record = resolve_inventory_barcode(raw_barcode)
    if not barcode_record:
        return jsonify(
            {
                "success": False,
                "error_code": "barcode_not_found",
                "message": "Okutulan birim barkodu sistemde bulunamadı.",
            }
        ), 404

    if barcode_record.status != "available":
        return jsonify(
            {
                "success": False,
                "error_code": "barcode_not_available",
                "message": "Bu birim barkodu kullanılabilir mağaza stokunda değil.",
            }
        ), 409

    line = next((item for item in inventory_count.lines if item.product_id == barcode_record.product_id), None)
    if not line:
        return jsonify(
            {
                "success": False,
                "error_code": "barcode_not_in_inventory_count",
                "message": "Okutulan barkod bu sayım listesinde bulunamadı.",
            }
        ), 400

    existing_scan = InventoryCountScan.query.filter_by(
        inventory_count_id=inventory_count.id,
        product_barcode_id=barcode_record.id,
    ).first()
    if existing_scan:
        return jsonify(
            {
                "success": False,
                "error_code": "barcode_already_counted",
                "message": "Bu barkodu daha önce okuttunuz.",
            }
        ), 409

    previous_scan_count = len(line.scans)
    scan_record = InventoryCountScan(
        inventory_count=inventory_count,
        line=line,
        product_barcode=barcode_record,
        barcode_value=barcode_record.barcode,
    )
    db.session.add(scan_record)
    line.counted_quantity = previous_scan_count + 1
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            {
                "success": False,
                "error_code": "barcode_already_counted",
                "message": "Bu barkodu daha önce okuttunuz.",
            }
        ), 409
    summary = build_count_summary(inventory_count)
    return jsonify(
        {
            "success": True,
            "message": f"{barcode_record.product.name} sayım listesine eklendi.",
            "line": {
                "id": line.id,
                "counted_quantity": line.counted_quantity,
                "variance_quantity": line.variance_quantity,
                "variance_amount": str(line.variance_amount),
            },
            "scan": {
                "id": scan_record.id,
                "barcode": scan_record.barcode_value,
                "remove_url": url_for(
                    "inventory_counts.remove_scan",
                    count_id=inventory_count.id,
                    scan_id=scan_record.id,
                ),
            },
            "summary": {
                "positive_quantity": summary["positive_quantity"],
                "negative_quantity": summary["negative_quantity"],
                "positive_amount": str(summary["positive_amount"]),
                "negative_amount": str(summary["negative_amount"]),
                "net_amount": str(summary["net_amount"]),
            },
        }
    )


@bp.route("/<int:count_id>/scans/<int:scan_id>/remove", methods=["POST"])
def remove_scan(count_id, scan_id):
    inventory_count = InventoryCount.query.get_or_404(count_id)
    if inventory_count.status == "approved":
        return jsonify(
            {
                "success": False,
                "error_code": "inventory_count_approved",
                "message": "Onaylanmış sayımdan barkod kaldırılamaz.",
            }
        ), 400

    scan_record = InventoryCountScan.query.filter_by(
        id=scan_id,
        inventory_count_id=inventory_count.id,
    ).first_or_404()
    line = scan_record.line
    barcode_value = scan_record.barcode_value
    remaining_scan_count = max(len(line.scans) - 1, 0)
    db.session.delete(scan_record)
    line.counted_quantity = remaining_scan_count
    db.session.commit()
    summary = build_count_summary(inventory_count)
    return jsonify(
        {
            "success": True,
            "message": f"{barcode_value} sayımdan çıkarıldı.",
            "line": {
                "id": line.id,
                "counted_quantity": line.counted_quantity,
                "variance_quantity": line.variance_quantity,
                "variance_amount": str(line.variance_amount),
            },
            "summary": {
                "positive_quantity": summary["positive_quantity"],
                "negative_quantity": summary["negative_quantity"],
                "positive_amount": str(summary["positive_amount"]),
                "negative_amount": str(summary["negative_amount"]),
                "net_amount": str(summary["net_amount"]),
            },
        }
    )


@bp.route("/<int:count_id>/approve", methods=["POST"])
def approve(count_id):
    inventory_count = InventoryCount.query.get_or_404(count_id)
    if inventory_count.status == "approved":
        flash("Bu sayım listesi zaten onaylanmış.", "success")
        return redirect(url_for("inventory_counts.detail", count_id=count_id))

    for line in inventory_count.lines:
        scans = list(line.scans)
        scanned_barcode_ids = {scan.product_barcode_id for scan in scans}
        available_barcodes = (
            ProductBarcode.query.filter_by(product_id=line.product_id, status="available")
            .order_by(ProductBarcode.sequence_no.asc())
            .all()
        )
        available_ids = {barcode.id for barcode in available_barcodes}
        if len(scanned_barcode_ids) != len(scans) or not scanned_barcode_ids <= available_ids:
            flash(
                f"{line.product.name} için okutulan barkodlardan biri artık kullanılabilir stokta değil. "
                "Sayımı yenileyip tekrar deneyin.",
                "error",
            )
            return redirect(url_for("inventory_counts.detail", count_id=count_id))
        if line.product.stock_quantity != len(available_barcodes):
            flash(
                f"{line.product.name} stok miktarı ile kullanılabilir birim barkodu sayısı uyuşmuyor. "
                "Sayım uygulanmadan önce stok bütünlüğünü düzeltin.",
                "error",
            )
            return redirect(url_for("inventory_counts.detail", count_id=count_id))

    for line in inventory_count.lines:
        quantity_before = line.product.stock_quantity
        scanned_barcode_ids = {scan.product_barcode_id for scan in line.scans}
        available_barcodes = (
            ProductBarcode.query.filter_by(product_id=line.product_id, status="available")
            .order_by(ProductBarcode.sequence_no.asc())
            .all()
        )
        removed_barcodes = [barcode for barcode in available_barcodes if barcode.id not in scanned_barcode_ids]
        for barcode in removed_barcodes:
            db.session.delete(barcode)
        line.counted_quantity = len(scanned_barcode_ids)
        line.product.stock_quantity = line.counted_quantity
        record_inventory_movement(
            line.product,
            transaction_type="count_in" if line.counted_quantity > quantity_before else "count_out",
            quantity_before=quantity_before,
            quantity_after=line.counted_quantity,
            source_type="inventory_count",
            source_id=inventory_count.id,
            source_reference=f"Sayım #{inventory_count.document_no}",
            barcode_values=[barcode.barcode for barcode in removed_barcodes],
            note=inventory_count.name,
        )

    inventory_count.status = "approved"
    inventory_count.approved_at = datetime.utcnow()
    db.session.commit()
    flash("Sayım sisteme uygulandı. Stoklar sayım değerleri ile güncellendi.", "success")
    return redirect(url_for("inventory_counts.detail", count_id=count_id))
