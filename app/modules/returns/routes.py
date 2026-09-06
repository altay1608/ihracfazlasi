from collections import defaultdict
from decimal import Decimal

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Product, ProductBarcode, Return, ReturnItem, Sale, SaleItem
from app.services.customer_orders import (
    calculate_order_line_return_gross,
    refresh_customer_order_return_status,
    register_returned_quantity,
)
from app.modules.returns.forms import ReturnForm
from app.services.finance import sync_return_finance
from app.services.inventory_history import record_inventory_movement
from app.services.product_inventory import (
    PRODUCT_VAT_MULTIPLIER,
    get_customer_gross_amount,
    release_barcodes_from_sale,
    resolve_unit_barcode,
)
from app.utils import RETURN_TYPES, is_ajax_request, is_modal_request, quantize_amount


bp = Blueprint("returns", __name__, url_prefix="/returns")


def get_return_listing():
    return (
        Return.query.options(
            joinedload(Return.items).joinedload(ReturnItem.product),
            joinedload(Return.items).joinedload(ReturnItem.original_sale_item),
            joinedload(Return.original_sale),
        )
        .order_by(Return.return_date.desc())
        .all()
    )


def render_return_form(form, sale=None, status_code=200):
    template_name = "returns/_create_modal.html" if is_modal_request() else "returns/form.html"
    return (
        render_template(
            template_name,
            form=form,
            sale=sale,
            return_types=RETURN_TYPES,
        ),
        status_code,
    )


def build_return_receipt_context(return_record):
    line_items = []
    total_refund = Decimal("0.00")
    receipt_refunds = calculate_receipt_refund_allocations(return_record)
    gross_refunds = calculate_receipt_gross_allocations(return_record, receipt_refunds)

    for item_index, item in enumerate(return_record.items):
        gross_refund_amount = gross_refunds[item_index]
        total_refund += gross_refund_amount
        line_items.append(
            {
                "name": getattr(item, "display_product_name", None) or item.product.name,
                "variant": getattr(item, "display_product_variant", None),
                "order_line_reference": getattr(item, "order_line_reference", None),
                "quantity": item.quantity,
                "refund_amount": gross_refund_amount,
                "type": "Yeni Urun" if return_record.type == "degisim" and item.refund_amount < 0 else "Iade",
            }
        )

    return {
        "line_items": line_items,
        "total_refund": quantize_amount(total_refund),
        "vat_rate": int((PRODUCT_VAT_MULTIPLIER - Decimal("1.00")) * 100),
    }


def calculate_receipt_refund_allocations(return_record):
    allocations = {}
    grouped_items = defaultdict(list)

    for item_index, item in enumerate(return_record.items):
        if quantize_amount(item.refund_amount or 0) <= 0:
            continue
        original_sale_item = find_original_sale_item(return_record, item)
        if original_sale_item:
            grouped_items[original_sale_item.id].append((item_index, item, original_sale_item))

    for grouped_rows in grouped_items.values():
        original_sale_item = grouped_rows[0][2]
        total_quantity = sum(item.quantity for _, item, _ in grouped_rows)
        target_refund = calculate_return_item_net_refund(
            return_record.original_sale,
            original_sale_item,
            total_quantity,
        )
        remaining_refund = target_refund

        for row_index, (item_index, item, _) in enumerate(grouped_rows):
            if row_index == len(grouped_rows) - 1:
                allocated_refund = remaining_refund
            else:
                allocated_refund = min(
                    calculate_return_item_net_refund(
                        return_record.original_sale,
                        original_sale_item,
                        item.quantity,
                    ),
                    remaining_refund,
                )
            allocations[item_index] = allocated_refund
            remaining_refund = quantize_amount(remaining_refund - allocated_refund)

    return allocations


def calculate_receipt_gross_allocations(return_record, net_allocations):
    grouped_indexes = defaultdict(list)
    resolved_net_amounts = {}
    allocations = {}

    for item_index, item in enumerate(return_record.items):
        stored_gross = getattr(item, "gross_refund_amount", None)
        if stored_gross is not None:
            allocations[item_index] = quantize_amount(stored_gross)
            continue
        net_amount = net_allocations.get(item_index, quantize_amount(item.refund_amount or 0))
        resolved_net_amounts[item_index] = net_amount
        original_sale_item = find_original_sale_item(return_record, item) if net_amount > 0 else None
        if original_sale_item:
            group_key = ("return", original_sale_item.id)
        elif net_amount < 0:
            group_key = ("replacement", get_item_product_id(item))
        else:
            group_key = ("item", item_index)
        grouped_indexes[group_key].append(item_index)

    for item_indexes in grouped_indexes.values():
        target_gross = get_customer_gross_amount(
            sum((resolved_net_amounts[item_index] for item_index in item_indexes), Decimal("0.00"))
        )
        allocated_gross = Decimal("0.00")
        for position, item_index in enumerate(item_indexes):
            if position == len(item_indexes) - 1:
                line_gross = quantize_amount(target_gross - allocated_gross)
            else:
                line_gross = get_customer_gross_amount(resolved_net_amounts[item_index])
            allocations[item_index] = line_gross
            allocated_gross = quantize_amount(allocated_gross + line_gross)

    return allocations


def get_model_id(obj):
    return getattr(obj, "id", None)


def get_item_product_id(item):
    product_id = getattr(item, "product_id", None)
    if product_id is not None:
        return product_id
    return get_model_id(getattr(item, "product", None))


def find_original_sale_item(return_record, return_item):
    linked_line = getattr(return_item, "original_sale_item", None)
    if linked_line is not None:
        return linked_line

    original_sale = getattr(return_record, "original_sale", None)
    if not original_sale:
        return None

    return_product_id = get_item_product_id(return_item)
    if return_product_id is None:
        return None

    matches = []
    for sale_item in getattr(original_sale, "items", []) or []:
        if get_item_product_id(sale_item) == return_product_id:
            matches.append(sale_item)

    if len(matches) != 1:
        return None
    return matches[0]


def get_return_receipt_net_amount(return_record, return_item):
    stored_amount = quantize_amount(return_item.refund_amount or 0)
    if stored_amount <= 0:
        return stored_amount

    original_sale_item = find_original_sale_item(return_record, return_item)
    if not original_sale_item:
        return stored_amount

    return calculate_return_item_net_refund(
        return_record.original_sale,
        original_sale_item,
        return_item.quantity,
    )


@bp.route("/")
def index():
    return_records = get_return_listing()
    if request.args.get("partial") == "list":
        return render_template("returns/_list_section.html", return_records=return_records, return_types=RETURN_TYPES)
    return render_template("returns/index.html", return_records=return_records, return_types=RETURN_TYPES)


@bp.route("/create", methods=["GET", "POST"])
def create():
    sale = None
    lookup_sale_id = request.args.get("sale_id", "").strip()
    form = ReturnForm()

    if request.method == "GET" and not lookup_sale_id and not is_modal_request():
        flash("İade / değişim başlatmak için satış ID girin veya satış listesinden işlem başlatın.", "error")
        return redirect(url_for("returns.index"))

    if lookup_sale_id.isdigit():
        sale = (
            Sale.query.options(
                joinedload(Sale.items).joinedload(SaleItem.product),
                joinedload(Sale.items).joinedload(SaleItem.product_barcodes),
            )
            .filter_by(document_no=int(lookup_sale_id))
            .first()
        )
        if sale and not form.original_sale_id.data:
            form.original_sale_id.data = str(sale.document_no)
        elif lookup_sale_id and not sale and request.method == "GET":
            flash("Girilen satış ID için kayıt bulunamadı.", "error")
            return redirect(url_for("returns.index"))
    elif request.method == "POST" and (form.original_sale_id.data or "").isdigit():
        sale = (
            Sale.query.options(
                joinedload(Sale.items).joinedload(SaleItem.product),
                joinedload(Sale.items).joinedload(SaleItem.product_barcodes),
            )
            .filter_by(document_no=int(form.original_sale_id.data))
            .first()
        )

    if form.validate_on_submit():
        sale = (
            Sale.query.options(
                joinedload(Sale.items).joinedload(SaleItem.product),
                joinedload(Sale.items).joinedload(SaleItem.product_barcodes),
            )
            .filter_by(document_no=int(form.original_sale_id.data))
            .first()
        )
        if not sale:
            if is_ajax_request():
                html, status_code = render_return_form(form, sale=None, status_code=404)
                return jsonify({"success": False, "html": html, "message": "Orijinal satış bulunamadı."}), status_code
            flash("Orijinal satış bulunamadı.", "error")
            return redirect(url_for("returns.create"))

        line_inputs = collect_line_inputs(request.form)
        if not line_inputs:
            if is_ajax_request():
                html, status_code = render_return_form(form, sale=sale, status_code=400)
                return jsonify({"success": False, "html": html, "message": "En az bir ürün için barkod seçin."}), status_code
            flash("En az bir ürün için barkod seçin.", "error")
            return render_return_form(form, sale=sale, status_code=400)

        try:
            return_record, stock_movements = build_return_record(
                sale,
                form.type.data,
                form.reason.data.strip(),
                (form.note.data or "").strip(),
                line_inputs,
            )
            db.session.add(return_record)
            db.session.flush()
            for movement in stock_movements:
                record_inventory_movement(
                    movement["product"],
                    transaction_type=movement["transaction_type"],
                    quantity_before=movement["quantity_before"],
                    quantity_after=movement["quantity_after"],
                    source_type="return",
                    source_id=return_record.id,
                    source_reference=f"İade #{return_record.document_no}",
                    barcode_values=movement["barcode_values"],
                    note=movement.get("note"),
                )
            sync_return_finance(return_record)
            db.session.commit()
            if is_ajax_request():
                return jsonify(
                    {
                        "success": True,
                        "message": "İade / değişim işlemi kaydedildi.",
                        "redirect_url": url_for("returns.index"),
                        "persist_message_after_redirect": True,
                    }
                )
            flash("İade / değişim işlemi kaydedildi.", "success")
            return redirect(url_for("returns.index"))
        except ValueError as exc:
            db.session.rollback()
            if is_ajax_request():
                html, status_code = render_return_form(form, sale=sale, status_code=400)
                return jsonify({"success": False, "html": html, "message": str(exc)}), status_code
            flash(str(exc), "error")

    if is_ajax_request() and form.errors:
        html, status_code = render_return_form(form, sale=sale, status_code=400)
        return jsonify({"success": False, "html": html}), status_code
    return render_return_form(form, sale=sale)


@bp.route("/<int:return_id>/receipt")
def receipt(return_id):
    return_record = (
        Return.query.options(
            joinedload(Return.items).joinedload(ReturnItem.product),
            joinedload(Return.items).joinedload(ReturnItem.original_sale_item),
            joinedload(Return.original_sale).joinedload(Sale.items).joinedload(SaleItem.product),
        )
        .filter_by(id=return_id)
        .first_or_404()
    )
    receipt = build_return_receipt_context(return_record)
    return render_template(
        "returns/receipt.html",
        return_record=return_record,
        return_types=RETURN_TYPES,
        receipt=receipt,
    )


def collect_line_inputs(form_data):
    rows = []
    for key in form_data.keys():
        if key.startswith("return_barcode_"):
            identity_parts = key.replace("return_barcode_", "", 1).split("_", 1)
            if len(identity_parts) != 2 or not all(part.isdigit() for part in identity_parts):
                continue
            sale_item_id, barcode_id = (int(part) for part in identity_parts)
            barcode_value = str(form_data.get(key) or "").strip()
            if not barcode_value:
                continue
            rows.append(
                {
                    "sale_item_id": sale_item_id,
                    "quantity": 1,
                    "barcode_values": [barcode_value],
                    "replacement_product_lookup": str(
                        form_data.get(f"replacement_barcode_{sale_item_id}_{barcode_id}") or ""
                    ).strip(),
                }
            )
            continue
        if not key.startswith("return_barcodes_"):
            continue
        sale_item_id = key.replace("return_barcodes_", "")
        barcode_values = [value.strip() for value in form_data.getlist(key) if str(value).strip()]
        if not barcode_values:
            continue
        sale_item_id = int(sale_item_id)
        replacement_raw = form_data.get(f"replacement_product_{sale_item_id}", "").strip()
        rows.append(
            {
                "sale_item_id": sale_item_id,
                "quantity": len(barcode_values),
                "barcode_values": barcode_values,
                "replacement_product_lookup": replacement_raw,
            }
        )
    return rows


def resolve_replacement_barcodes(lookup_value, quantity):
    barcode_values = [value.strip() for value in str(lookup_value or "").split(";") if value.strip()]
    if len(barcode_values) != quantity or len(set(barcode_values)) != quantity:
        raise ValueError("Değişimde her yeni ürün için tam birim barkodunu ayrı ayrı okutun.")

    with db.session.no_autoflush:
        records = [resolve_unit_barcode(value, status="available") for value in barcode_values]
    if any(record is None for record in records):
        raise ValueError(
            "Yeni ürün birim barkodlarından biri bulunamadı veya kullanılabilir değil. Kodu -01 uzantısı dahil eksiksiz okutun."
        )
    if len({record.product_id for record in records}) != 1:
        raise ValueError("Aynı değişim satırındaki yeni ürün barkodları tek bir ürüne ait olmalıdır.")
    return records


def get_sale_item_net_total(sale_item):
    gross_line = quantize_amount(sale_item.unit_price * sale_item.quantity)
    line_discount = quantize_amount(sale_item.discount_amount or 0)
    return quantize_amount(gross_line - line_discount)


def calculate_return_item_net_refund(sale, sale_item, quantity):
    base_refund = quantize_amount(sale_item.unit_price * quantity)
    line_discount_share = quantize_amount(
        (sale_item.discount_amount / sale_item.quantity) * quantity if sale_item.quantity else 0
    )
    item_net_before_footer = quantize_amount(base_refund - line_discount_share)

    sale_line_subtotal = quantize_amount(sum((get_sale_item_net_total(item) for item in sale.items), Decimal("0.00")))
    sale_line_discount_total = quantize_amount(
        sum((quantize_amount(item.discount_amount or 0) for item in sale.items), Decimal("0.00"))
    )
    footer_discount = quantize_amount((sale.total_discount or Decimal("0.00")) - sale_line_discount_total)
    if footer_discount < 0:
        footer_discount = Decimal("0.00")
    if footer_discount > sale_line_subtotal:
        footer_discount = sale_line_subtotal

    footer_discount_share = Decimal("0.00")
    if footer_discount and sale_line_subtotal:
        footer_discount_share = quantize_amount((item_net_before_footer / sale_line_subtotal) * footer_discount)

    return max(quantize_amount(item_net_before_footer - footer_discount_share), Decimal("0.00"))


def calculate_line_refund_allocations(sale, sale_item_map, line_inputs):
    grouped_row_indexes = defaultdict(list)
    for row_index, row in enumerate(line_inputs):
        grouped_row_indexes[row["sale_item_id"]].append(row_index)

    allocations = {}
    for sale_item_id, row_indexes in grouped_row_indexes.items():
        sale_item = sale_item_map.get(sale_item_id)
        if not sale_item:
            raise ValueError("Satış satırlarından biri bulunamadı.")

        total_quantity = sum(line_inputs[row_index]["quantity"] for row_index in row_indexes)
        if total_quantity > sale_item.quantity:
            raise ValueError(
                f"{sale_item.product_name_snapshot} için seçilen barkod adedi satış adedini aşamaz."
            )

        target_refund = calculate_return_item_net_refund(sale, sale_item, total_quantity)
        remaining_refund = target_refund
        for position, row_index in enumerate(row_indexes):
            if position == len(row_indexes) - 1:
                allocated_refund = remaining_refund
            else:
                allocated_refund = min(
                    calculate_return_item_net_refund(
                        sale,
                        sale_item,
                        line_inputs[row_index]["quantity"],
                    ),
                    remaining_refund,
                )
            allocations[row_index] = allocated_refund
            remaining_refund = quantize_amount(remaining_refund - allocated_refund)

    return allocations


def calculate_line_gross_refund_allocations(sale_item_map, line_inputs):
    grouped_row_indexes = defaultdict(list)
    for row_index, row in enumerate(line_inputs):
        grouped_row_indexes[row["sale_item_id"]].append(row_index)

    allocations = {}
    for sale_item_id, row_indexes in grouped_row_indexes.items():
        sale_item = sale_item_map.get(sale_item_id)
        if not sale_item:
            raise ValueError("Satış satırlarından biri bulunamadı.")

        offset = int(sale_item.returned_quantity or 0)
        for row_index in row_indexes:
            quantity = int(line_inputs[row_index]["quantity"] or 0)
            allocations[row_index] = calculate_order_line_return_gross(
                sale_item,
                quantity,
                already_returned=offset,
            )
            offset += quantity
    return allocations


def validate_unit_barcode_selections(line_inputs, return_type):
    returned_barcodes = [
        barcode
        for row in line_inputs
        for barcode in row.get("barcode_values", [])
        if barcode
    ]
    if len(returned_barcodes) != len(set(returned_barcodes)):
        raise ValueError("Aynı iade birim barkodu işleme birden fazla kez eklenemez.")

    if return_type != "degisim":
        return

    replacement_barcodes = [
        barcode.strip()
        for row in line_inputs
        for barcode in str(row.get("replacement_product_lookup") or "").split(";")
        if barcode.strip()
    ]
    if len(replacement_barcodes) != len(set(replacement_barcodes)):
        raise ValueError("Aynı yeni ürün birim barkodu değişime birden fazla kez eklenemez.")


def build_return_record(sale, return_type, reason, note, line_inputs):
    sale_item_map = {item.id: item for item in sale.items}
    validate_unit_barcode_selections(line_inputs, return_type)
    refund_allocations = calculate_line_refund_allocations(sale, sale_item_map, line_inputs)
    gross_refund_allocations = calculate_line_gross_refund_allocations(sale_item_map, line_inputs)
    return_record = Return(
        site_id=sale.site_id,
        store_id=sale.store_id,
        original_sale=sale,
        reason=reason,
        note=note or None,
        type=return_type,
        status="tamamlandi",
    )
    stock_movements = []

    for row_index, row in enumerate(line_inputs):
        sale_item = sale_item_map.get(row["sale_item_id"])
        if not sale_item:
            raise ValueError("Satış satırlarından biri bulunamadı.")

        original_product = sale_item.product
        quantity_before = original_product.stock_quantity
        released_barcodes = release_barcodes_from_sale(sale_item, row.get("barcode_values"))
        net_refund = refund_allocations[row_index]

        return_record.items.append(
            ReturnItem(
                site_id=sale_item.site_id,
                store_id=sale_item.store_id,
                product=original_product,
                original_sale_item=sale_item,
                quantity=row["quantity"],
                refund_amount=net_refund,
                gross_refund_amount=gross_refund_allocations[row_index],
                unit_cost_snapshot=sale_item.unit_cost_snapshot,
                product_code_snapshot=sale_item.product_code_snapshot,
                product_name_snapshot=sale_item.product_name_snapshot,
                product_variant_snapshot=sale_item.product_variant_snapshot,
            )
        )
        register_returned_quantity(sale_item, row["quantity"])
        stock_movements.append(
            {
                "product": original_product,
                "transaction_type": "return_in",
                "quantity_before": quantity_before,
                "quantity_after": original_product.stock_quantity,
                "barcode_values": [barcode.barcode for barcode in released_barcodes],
                "note": reason,
            }
        )

        if return_type == "degisim":
            replacement_lookup = (row.get("replacement_product_lookup") or "").strip()
            if not replacement_lookup:
                raise ValueError(f"{original_product.name} için yeni ürün birim barkodunu girin.")
            replacement_barcodes = resolve_replacement_barcodes(replacement_lookup, row["quantity"])
            replacement_product = replacement_barcodes[0].product
            if replacement_product.stock_quantity < row["quantity"]:
                raise ValueError(f"{replacement_product.name} için yeterli stok yok.")

            replacement_quantity_before = replacement_product.stock_quantity
            for barcode in replacement_barcodes:
                barcode.status = "sold"

            replacement_product.stock_quantity -= row["quantity"]
            replacement_total = quantize_amount(replacement_product.sale_price * row["quantity"])
            return_record.items.append(
                ReturnItem(
                    site_id=sale.site_id,
                    store_id=sale.store_id,
                    product=replacement_product,
                    quantity=row["quantity"],
                    refund_amount=quantize_amount(replacement_total * Decimal("-1")),
                    gross_refund_amount=quantize_amount(
                        get_customer_gross_amount(replacement_total) * Decimal("-1")
                    ),
                    unit_cost_snapshot=quantize_amount(replacement_product.purchase_price or 0),
                    product_code_snapshot=replacement_product.product_code,
                    product_name_snapshot=replacement_product.name,
                    product_variant_snapshot=replacement_product.variant,
                )
            )

            stock_movements.append(
                {
                    "product": replacement_product,
                    "transaction_type": "exchange_out",
                    "quantity_before": replacement_quantity_before,
                    "quantity_after": replacement_product.stock_quantity,
                    "barcode_values": [barcode.barcode for barcode in replacement_barcodes],
                    "note": reason,
                }
            )

    refresh_customer_order_return_status(sale)
    return return_record, stock_movements
