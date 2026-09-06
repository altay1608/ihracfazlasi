from datetime import date, datetime, timedelta
import os
from decimal import Decimal
from urllib.parse import quote

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.data import TR_LOCATIONS
from app.extensions import db
from app.models import Product, Sale, SaleItem
from app.services.customer_orders import prepare_customer_order
from app.services.finance import sync_sale_finance
from app.services.inventory_history import record_inventory_movement
from app.services.product_inventory import release_barcodes_from_sale, reserve_barcodes_for_sale, round_customer_price
from app.services.reference_data import get_payment_method_choices, get_payment_method_map
from app.utils import istanbul_day_start_utc, now_in_istanbul, parse_iso_date, quantize_amount


bp = Blueprint("sales", __name__, url_prefix="/sales")

VAT_RATE = Decimal("0.10")
VAT_MULTIPLIER = Decimal("1.10")
STORE_INFO = {
    "name": os.getenv("STORE_NAME", "İhraç Fazlası Giyim"),
    "address_line_1": os.getenv("STORE_ADDRESS_LINE_1", ""),
    "address_line_2": os.getenv("STORE_ADDRESS_LINE_2", ""),
    "address_line_3": os.getenv("STORE_ADDRESS_LINE_3", ""),
    "instagram": os.getenv("STORE_INSTAGRAM", ""),
    "cashier": os.getenv("STORE_CASHIER_LABEL", "Mağaza Yetkilisi"),
}


def clean_optional_text(value, limit):
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    return cleaned[:limit]


def build_customer_payload(payload):
    customer = payload.get("customer") or {}
    return {
        "customer_name": clean_optional_text(customer.get("customer_name"), 150),
        "customer_phone": clean_optional_text(customer.get("customer_phone"), 40),
        "customer_mobile": clean_optional_text(customer.get("customer_mobile"), 40),
        "customer_email": clean_optional_text(customer.get("customer_email"), 150),
        "customer_city": clean_optional_text(customer.get("customer_city"), 120),
        "customer_address": clean_optional_text(customer.get("customer_address"), 1000),
        "customer_tax_office": clean_optional_text(customer.get("customer_tax_office"), 120),
        "customer_tax_number": clean_optional_text(customer.get("customer_tax_number"), 40),
        "customer_note": clean_optional_text(customer.get("customer_note"), 200),
    }


def has_customer_data(sale):
    return any(
        getattr(sale, field)
        for field in (
            "customer_name",
            "customer_phone",
            "customer_mobile",
            "customer_email",
            "customer_city",
            "customer_address",
            "customer_tax_office",
            "customer_tax_number",
            "customer_note",
        )
    )


def serialize_sale_customer(sale):
    return {
        "sale_id": sale.id,
        "sale_no": sale.document_no,
        "name": sale.customer_name or "",
        "phone": sale.customer_phone or "",
        "mobile": sale.customer_mobile or "",
        "email": sale.customer_email or "",
        "city": sale.customer_city or "",
        "address": sale.customer_address or "",
        "tax_office": sale.customer_tax_office or "",
        "tax_number": sale.customer_tax_number or "",
        "note": sale.customer_note or "",
        "last_used_at": sale.sale_date.isoformat() if sale.sale_date else "",
    }


def customer_signature(sale):
    return (
        sale.customer_name or "",
        sale.customer_phone or "",
        sale.customer_mobile or "",
        sale.customer_email or "",
        sale.customer_tax_number or "",
    )


def collect_customer_snapshots(query, limit):
    seen = set()
    results = []
    for sale in query:
        if not has_customer_data(sale):
            continue
        signature = customer_signature(sale)
        if signature in seen:
            continue
        seen.add(signature)
        results.append(serialize_sale_customer(sale))
        if len(results) >= limit:
            break
    return results


def build_sale_transaction_code(sale):
    sale_day = (sale.sale_date or sale.created_at).strftime("%Y%m%d")
    site = getattr(sale, "site", None)
    site_code = site.code if site else "SITE"
    document_no = getattr(sale, "document_no", None) or sale.id
    return f"TX-{site_code}-{sale_day}-{document_no:03d}"


def calculate_sale_breakdown(sale):
    line_subtotal = quantize_amount(sum((item.line_total for item in sale.items), Decimal("0.00")))
    line_discount_total = quantize_amount(sum((item.discount_amount for item in sale.items), Decimal("0.00")))
    footer_discount_amount = quantize_amount((sale.total_discount or Decimal("0.00")) - line_discount_total)

    if footer_discount_amount < 0:
        footer_discount_amount = Decimal("0.00")
    if footer_discount_amount > line_subtotal:
        footer_discount_amount = line_subtotal

    stored_total = getattr(sale, "total_amount", None)
    if stored_total is None:
        gross_total = round_customer_price(line_subtotal * VAT_MULTIPLIER)
    else:
        gross_total = quantize_amount(stored_total or 0)
    net_subtotal = quantize_amount(gross_total / VAT_MULTIPLIER)
    vat_amount = quantize_amount(gross_total - net_subtotal)

    return {
        "line_subtotal": line_subtotal,
        "line_discount_total": line_discount_total,
        "footer_discount_amount": footer_discount_amount,
        "net_subtotal": net_subtotal,
        "vat_amount": vat_amount,
        "gross_total": gross_total,
    }


def build_sale_receipt_context(sale):
    now = datetime.now()
    breakdown = calculate_sale_breakdown(sale)
    receipt_url = request.url_root.rstrip("/") + url_for("sales.receipt", sale_id=sale.id)
    line_items = []
    for item in sale.items:
        item_name = getattr(item, "product_name_snapshot", None) or item.product.name
        item_variant = getattr(item, "product_variant_snapshot", None)
        if item_variant is None:
            item_variant = getattr(item.product, "variant", None)
        if item_variant:
            item_name = f"{item_name} ({item_variant})"
        item_gross = getattr(item, "gross_amount", None)
        if item_gross is None:
            item_gross = round_customer_price(item.line_total * VAT_MULTIPLIER)
        line_items.append(
            {
                "name": item_name,
                "quantity": item.quantity,
                "vat_rate": int(VAT_RATE * 100),
                "gross_total": item_gross,
            }
        )
    return {
        "tx_code": build_sale_transaction_code(sale),
        "lookup_id": f"TX-{(getattr(sale, 'document_no', None) or sale.id):05d}",
        "cashier_name": STORE_INFO["cashier"],
        "store": STORE_INFO,
        "net_subtotal": breakdown["net_subtotal"],
        "vat_amount": breakdown["vat_amount"],
        "line_items": line_items,
        "print_time": now.strftime("%H:%M"),
        "qr_url": f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={quote(receipt_url, safe='')}",
        "receipt_url": receipt_url,
    }


def serialize_sale_for_edit(sale):
    items = []
    for item in sale.items:
        barcode_records = sorted(item.product_barcodes, key=lambda barcode: barcode.sequence_no)
        items.append(
            {
                "id": item.product.id,
                "product_id": item.product.id,
                "name": item.product_name_snapshot,
                "variant": item.product_variant_snapshot,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "product_code": item.product_code_snapshot,
                "max_quantity": item.product.stock_quantity + item.quantity,
                "scanned_barcodes": [barcode.barcode for barcode in barcode_records],
                "scanned_barcode_ids": [barcode.id for barcode in barcode_records],
            }
        )
    return items


def get_sale_edit_discount_amount(sale):
    line_subtotal = quantize_amount(
        sum((item.unit_price * item.quantity for item in sale.items), Decimal("0.00"))
    )
    gross_before_discount = round_customer_price(line_subtotal * VAT_MULTIPLIER)
    discount_amount = quantize_amount(gross_before_discount - (sale.total_amount or Decimal("0.00")))
    return max(discount_amount, Decimal("0.00"))


def apply_sale_payload(sale, payload):
    payment_method = payload.get("payment_method")
    items = payload.get("items") or []
    payment_methods = dict(get_payment_method_choices(active_only=True))

    if payment_method not in payment_methods:
        raise ValueError("Geçerli bir ödeme yöntemi seçin.")
    if not items:
        raise ValueError("Sepet boş.")

    sale.payment_method = payment_method
    for key, value in build_customer_payload(payload).items():
        setattr(sale, key, value)

    subtotal_amount = Decimal("0.00")
    line_discount_total = Decimal("0.00")

    for item in items:
        product_id = int(item.get("product_id"))
        quantity = int(item.get("quantity"))
        discount_amount = quantize_amount(item.get("discount_amount", 0))
        scanned_barcodes = [value for value in (item.get("scanned_barcodes") or []) if str(value).strip()]

        if quantity <= 0:
            raise ValueError("Ürün adedi pozitif olmalıdır.")

        product = db.session.get(Product, product_id)
        if not product:
            raise ValueError("Sepetteki ürünlerden biri bulunamadı.")
        if product.stock_quantity < quantity:
            raise ValueError("Uygun stok miktarı yok, satış gerçekleştiremezsiniz.")

        unit_price = quantize_amount(item.get("unit_price", product.sale_price))
        gross_line_total = quantize_amount(unit_price * quantity)
        if discount_amount > gross_line_total:
            raise ValueError("Satır indirimi ürün toplamından büyük olamaz.")

        sale_item = SaleItem(
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
        )
        sale.items.append(sale_item)
        reserve_barcodes_for_sale(product, sale_item, quantity, scanned_barcodes)
        subtotal_amount += gross_line_total
        line_discount_total += discount_amount

    discountable_base = quantize_amount(subtotal_amount - line_discount_total)
    requested_target_total = payload.get("target_final_total")
    footer_discount_amount = quantize_amount(payload.get("footer_discount_amount", 0))

    if requested_target_total not in (None, ""):
        requested_target_total = quantize_amount(requested_target_total)
        if requested_target_total < 0:
            raise ValueError("Nihai tutar negatif olamaz.")
        pre_vat_target = quantize_amount(requested_target_total / VAT_MULTIPLIER)
        footer_discount_amount = quantize_amount(discountable_base - pre_vat_target)

    if footer_discount_amount < 0:
        footer_discount_amount = Decimal("0.00")
    if footer_discount_amount > discountable_base:
        footer_discount_amount = discountable_base

    net_subtotal = quantize_amount(discountable_base - footer_discount_amount)
    vat_amount = quantize_amount(net_subtotal * VAT_RATE)
    total_amount = round_customer_price(net_subtotal + vat_amount)
    total_discount = quantize_amount(line_discount_total + footer_discount_amount)

    sale.total_amount = total_amount
    sale.total_discount = total_discount

    return {
        "subtotal_amount": subtotal_amount,
        "line_discount_total": line_discount_total,
        "footer_discount_amount": footer_discount_amount,
        "vat_amount": quantize_amount(total_amount - quantize_amount(total_amount / VAT_MULTIPLIER)),
        "total_amount": total_amount,
    }


@bp.route("/")
def index():
    today = now_in_istanbul().date()
    start_date = parse_iso_date(request.args.get("date_from"), fallback=today)
    end_date = parse_iso_date(request.args.get("date_to"), fallback=start_date)
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    payment_methods = get_payment_method_map(active_only=False)
    sales = (
        Sale.query.options(
            joinedload(Sale.items).joinedload(SaleItem.product),
            joinedload(Sale.items).joinedload(SaleItem.product_barcodes),
        )
        .filter(
            Sale.sale_date >= istanbul_day_start_utc(start_date),
            Sale.sale_date < istanbul_day_start_utc(end_date + timedelta(days=1)),
        )
        .order_by(Sale.sale_date.desc())
        .all()
    )
    order_lines = [(sale, item) for sale in sales for item in sale.items]
    return render_template(
        "sales/index.html",
        sales=sales,
        order_lines=order_lines,
        start_date=start_date,
        end_date=end_date,
        payment_methods=payment_methods,
        vat_rate=float(VAT_RATE),
    )


@bp.route("/pos")
def pos():
    return render_template(
        "sales/pos.html",
        payment_methods=dict(get_payment_method_choices(active_only=True)),
        city_map=TR_LOCATIONS,
        vat_rate=float(VAT_RATE),
    )


@bp.route("/<int:sale_id>/edit")
def edit(sale_id):
    sale = (
        Sale.query.options(
            joinedload(Sale.items).joinedload(SaleItem.product),
            joinedload(Sale.items).joinedload(SaleItem.product_barcodes),
        )
        .filter_by(id=sale_id)
        .first_or_404()
    )
    if sale.order_status == "CANCELLED":
        flash("İptal edilmiş satış siparişi yeniden düzenlenemez.", "error")
        return redirect(url_for("sales.detail", sale_id=sale.id))
    line_edits_locked = any(int(item.returned_quantity or 0) > 0 for item in sale.items)
    return render_template(
        "sales/pos.html",
        sale=sale,
        sale_edit=True,
        initial_cart=serialize_sale_for_edit(sale),
        initial_customer=serialize_sale_customer(sale),
        initial_discount_amount=get_sale_edit_discount_amount(sale),
        line_edits_locked=line_edits_locked,
        payment_methods=dict(get_payment_method_choices(active_only=True)),
        city_map=TR_LOCATIONS,
        vat_rate=float(VAT_RATE),
    )


@bp.route("/customers/search")
def customer_search():
    query_text = request.args.get("q", "").strip()
    if len(query_text) < 2:
        return jsonify({"success": True, "results": []})

    like = f"%{query_text}%"
    query = (
        Sale.query.filter(
            or_(
                Sale.customer_name.ilike(like),
                Sale.customer_phone.ilike(like),
                Sale.customer_mobile.ilike(like),
                Sale.customer_email.ilike(like),
                Sale.customer_city.ilike(like),
                Sale.customer_tax_number.ilike(like),
            )
        )
        .order_by(Sale.sale_date.desc())
        .limit(40)
        .all()
    )
    return jsonify({"success": True, "results": collect_customer_snapshots(query, 8)})


@bp.route("/customers/recent")
def customer_recent():
    query = Sale.query.order_by(Sale.sale_date.desc()).limit(30).all()
    return jsonify({"success": True, "results": collect_customer_snapshots(query, 6)})


@bp.route("/<int:sale_id>")
def detail(sale_id):
    payment_methods = get_payment_method_map(active_only=False)
    return_date_from = request.args.get("return_date_from", "").strip()
    return_date_to = request.args.get("return_date_to", "").strip()
    sale = (
        Sale.query.options(
            joinedload(Sale.items).joinedload(SaleItem.product),
            joinedload(Sale.items).joinedload(SaleItem.product_barcodes),
        )
        .filter_by(id=sale_id)
        .first_or_404()
    )
    breakdown = calculate_sale_breakdown(sale)
    customer_fields = [
        ("Ad Soyad", sale.customer_name),
        ("Cep Telefonu", sale.customer_mobile),
        ("Mail", sale.customer_email),
        ("Şehir / İlçe", sale.customer_city),
        ("Adres", sale.customer_address),
        ("Vergi Dairesi", sale.customer_tax_office),
        ("VKN / TCKN", sale.customer_tax_number),
        ("Açıklama", sale.customer_note),
    ]
    return render_template(
        "sales/detail.html",
        sale=sale,
        payment_methods=payment_methods,
        vat_rate=float(VAT_RATE),
        net_subtotal=breakdown["net_subtotal"],
        vat_amount=breakdown["vat_amount"],
        line_subtotal=breakdown["line_subtotal"],
        customer_fields=customer_fields,
        return_date_from=return_date_from,
        return_date_to=return_date_to,
    )


@bp.route("/<int:sale_id>/receipt")
def receipt(sale_id):
    payment_methods = get_payment_method_map(active_only=False)
    sale = (
        Sale.query.options(
            joinedload(Sale.items).joinedload(SaleItem.product),
            joinedload(Sale.items).joinedload(SaleItem.product_barcodes),
        )
        .filter_by(id=sale_id)
        .first_or_404()
    )
    return render_template(
        "sales/receipt.html",
        sale=sale,
        payment_methods=payment_methods,
        vat_rate=int(VAT_RATE * 100),
        receipt=build_sale_receipt_context(sale),
        auto_print=True,
    )


@bp.route("/<int:sale_id>/update", methods=["POST"])
def update(sale_id):
    sale = (
        Sale.query.options(
            joinedload(Sale.items).joinedload(SaleItem.product),
            joinedload(Sale.items).joinedload(SaleItem.product_barcodes),
        )
        .filter_by(id=sale_id)
        .first_or_404()
    )
    if sale.order_status == "CANCELLED":
        return jsonify(
            {
                "success": False,
                "message": "İptal edilmiş satış siparişi yeniden düzenlenemez.",
            }
        ), 409
    payload = request.get_json(silent=True) or {}
    has_returned_lines = any(int(item.returned_quantity or 0) > 0 for item in sale.items)

    if has_returned_lines:
        try:
            for key, value in build_customer_payload(payload).items():
                setattr(sale, key, value)
            sale.revision_no = int(sale.revision_no or 1) + 1
            sale.updated_at = datetime.utcnow()
            sync_sale_finance(sale)
            db.session.commit()
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            return jsonify({"success": False, "message": str(exc)}), 400

        breakdown = calculate_sale_breakdown(sale)
        flash(f"Satış #{sale.document_no} müşteri ve açıklama bilgileri güncellendi.", "success")
        return jsonify(
            {
                "success": True,
                "message": "Sipariş bilgileri güncellendi; iade bağlantılı mali satırlar korundu.",
                "sale_id": sale.id,
                "redirect_url": url_for("sales.detail", sale_id=sale.id),
                "summary": {
                    "subtotal_amount": float(breakdown["line_subtotal"]),
                    "line_discount_total": float(breakdown["line_discount_total"]),
                    "footer_discount_amount": float(breakdown["footer_discount_amount"]),
                    "vat_amount": float(breakdown["vat_amount"]),
                    "total_amount": float(sale.total_amount),
                },
            }
        )

    stock_before = {item.product.id: (item.product, item.product.stock_quantity) for item in sale.items}

    try:
        for item in payload.get("items") or []:
            product_id = int(item.get("product_id"))
            product = Product.query.filter_by(id=product_id).with_for_update().one_or_none()
            if not product:
                raise ValueError("Sepetteki ürünlerden biri bulunamadı.")
            stock_before.setdefault(product.id, (product, product.stock_quantity))

        for sale_item in list(sale.items):
            release_barcodes_from_sale(sale_item, [barcode.barcode for barcode in sale_item.product_barcodes])
            db.session.delete(sale_item)
        db.session.flush()

        summary = apply_sale_payload(sale, payload)
        sale.revision_no = int(sale.revision_no or 1) + 1
        sale.updated_at = datetime.utcnow()
        prepare_customer_order(sale)
        for product, quantity_before in stock_before.values():
            transaction_type = "sale_update_in" if product.stock_quantity > quantity_before else "sale_update_out"
            record_inventory_movement(
                product,
                transaction_type=transaction_type,
                quantity_before=quantity_before,
                quantity_after=product.stock_quantity,
                source_type="sale",
                source_id=sale.id,
                source_reference=f"Satış #{sale.document_no}",
                note="Satış siparişi düzenleme",
            )
        sync_sale_finance(sale)
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 400

    flash(f"Satış #{sale.document_no} güncellendi.", "success")
    return jsonify(
        {
            "success": True,
            "message": "Satış güncellendi.",
            "sale_id": sale.id,
            "redirect_url": url_for("sales.detail", sale_id=sale.id),
            "summary": {
                "subtotal_amount": float(summary["subtotal_amount"]),
                "line_discount_total": float(summary["line_discount_total"]),
                "footer_discount_amount": float(summary["footer_discount_amount"]),
                "vat_amount": float(summary["vat_amount"]),
                "total_amount": float(summary["total_amount"]),
            },
        }
    )


@bp.route("/complete", methods=["POST"])
def complete():
    payload = request.get_json(silent=True) or {}
    payment_method = payload.get("payment_method")
    items = payload.get("items") or []
    payment_methods = dict(get_payment_method_choices(active_only=True))

    if payment_method not in payment_methods:
        return jsonify({"success": False, "message": "Geçerli bir ödeme yöntemi seçin."}), 400
    if not items:
        return jsonify({"success": False, "message": "Sepet boş."}), 400

    sale = Sale(payment_method=payment_method, **build_customer_payload(payload))
    subtotal_amount = Decimal("0.00")
    line_discount_total = Decimal("0.00")
    stock_movements = []

    try:
        for item in items:
            product_id = int(item.get("product_id"))
            quantity = int(item.get("quantity"))
            discount_amount = quantize_amount(item.get("discount_amount", 0))
            scanned_barcodes = [value for value in (item.get("scanned_barcodes") or []) if str(value).strip()]

            if quantity <= 0:
                raise ValueError("Ürün adedi pozitif olmalıdır.")

            product = Product.query.filter_by(id=product_id).with_for_update().one_or_none()
            if not product:
                raise ValueError("Sepetteki ürünlerden biri bulunamadı.")
            if product.stock_quantity < quantity:
                raise ValueError("Uygun stok miktarı yok, satış gerçekleştiremezsiniz.")

            unit_price = quantize_amount(item.get("unit_price", product.sale_price))
            gross_line_total = quantize_amount(unit_price * quantity)
            if discount_amount > gross_line_total:
                raise ValueError("Satır indirimi ürün toplamından büyük olamaz.")

            sale_item = SaleItem(
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                discount_amount=discount_amount,
            )
            sale.items.append(sale_item)
            quantity_before = product.stock_quantity
            allocated_barcodes = reserve_barcodes_for_sale(product, sale_item, quantity, scanned_barcodes)
            stock_movements.append(
                {
                    "product": product,
                    "quantity_before": quantity_before,
                    "quantity_after": product.stock_quantity,
                    "barcode_values": [barcode.barcode for barcode in allocated_barcodes],
                }
            )
            subtotal_amount += gross_line_total
            line_discount_total += discount_amount

        discountable_base = quantize_amount(subtotal_amount - line_discount_total)
        requested_target_total = payload.get("target_final_total")
        footer_discount_amount = quantize_amount(payload.get("footer_discount_amount", 0))

        if requested_target_total not in (None, ""):
            requested_target_total = quantize_amount(requested_target_total)
            if requested_target_total < 0:
                raise ValueError("Nihai tutar negatif olamaz.")
            pre_vat_target = quantize_amount(requested_target_total / VAT_MULTIPLIER)
            footer_discount_amount = quantize_amount(discountable_base - pre_vat_target)

        if footer_discount_amount < 0:
            footer_discount_amount = Decimal("0.00")
        if footer_discount_amount > discountable_base:
            footer_discount_amount = discountable_base

        net_subtotal = quantize_amount(discountable_base - footer_discount_amount)
        vat_amount = quantize_amount(net_subtotal * VAT_RATE)
        total_amount = round_customer_price(net_subtotal + vat_amount)
        total_discount = quantize_amount(line_discount_total + footer_discount_amount)

        sale.total_amount = total_amount
        sale.total_discount = total_discount
        sale.completed_at = datetime.utcnow()
        sale.updated_at = sale.completed_at
        prepare_customer_order(sale)

        db.session.add(sale)
        db.session.flush()
        for movement in stock_movements:
            record_inventory_movement(
                movement["product"],
                transaction_type="sale_out",
                quantity_before=movement["quantity_before"],
                quantity_after=movement["quantity_after"],
                source_type="sale",
                source_id=sale.id,
                source_reference=f"Satış #{sale.document_no}",
                barcode_values=movement["barcode_values"],
            )
        sync_sale_finance(sale)
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": str(exc)}), 400

    flash(f"Satış #{sale.document_no} başarıyla tamamlandı.", "success")
    return jsonify(
        {
            "success": True,
            "message": "Satış tamamlandı.",
            "sale_id": sale.id,
            "sale_no": sale.document_no,
            "redirect_url": url_for("sales.detail", sale_id=sale.id),
            "summary": {
                "subtotal_amount": float(subtotal_amount),
                "line_discount_total": float(line_discount_total),
                "footer_discount_amount": float(footer_discount_amount),
                "vat_amount": float(vat_amount),
                "total_amount": float(total_amount),
            },
        }
    )

