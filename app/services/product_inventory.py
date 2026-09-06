from decimal import Decimal, ROUND_FLOOR

from app.extensions import db
from app.models import Product, ProductBarcode, RetailMultiplier
from app.services.identity_access import get_active_site_id
from app.utils import quantize_amount


MIN_PRODUCT_CODE = 100000000001
PRODUCT_VAT_MULTIPLIER = Decimal("1.10")
ROUNDING_STEP = Decimal("10")
ROUNDING_MIDPOINT = Decimal("5")


def get_next_product_code(site_id=None):
    resolved_site_id = int(site_id or get_active_site_id())
    max_code = MIN_PRODUCT_CODE - 1

    for (value,) in db.session.query(Product.product_code).filter(Product.site_id == resolved_site_id).all():
        if value and str(value).isdigit():
            max_code = max(max_code, int(value))

    for (value,) in db.session.query(Product.barcode).filter(Product.site_id == resolved_site_id).all():
        if value and str(value).isdigit():
            max_code = max(max_code, int(value))

    return str(max(MIN_PRODUCT_CODE, max_code + 1))


def format_unit_barcode(product_code, sequence_no):
    return f"{product_code}-{int(sequence_no):02d}"


def resolve_unit_barcode(raw_barcode, *, status=None):
    raw_value = str(raw_barcode or "").strip()
    if not raw_value:
        return None

    query = ProductBarcode.query
    if status is not None:
        query = query.filter(ProductBarcode.status == status)

    return query.filter(ProductBarcode.barcode == raw_value).first()


def compute_sale_price(purchase_price, multiplier):
    purchase = Decimal(str(purchase_price or 0))
    ratio = Decimal(str(multiplier or 1))
    return quantize_amount(purchase * ratio)


def compute_sale_price_gross_target(purchase_price, multiplier):
    purchase = Decimal(str(purchase_price or 0))
    ratio = Decimal(str(multiplier or 1))
    return quantize_amount(purchase * PRODUCT_VAT_MULTIPLIER * ratio)


def round_customer_price(value):
    amount = quantize_amount(value or 0)
    whole_lira = amount.quantize(Decimal("1"), rounding=ROUND_FLOOR)
    cents = amount - whole_lira
    lower_ten = (whole_lira // ROUNDING_STEP) * ROUNDING_STEP
    midpoint = lower_ten + ROUNDING_MIDPOINT

    if cents == 0 and whole_lira == midpoint:
        return quantize_amount(midpoint)
    if amount <= midpoint:
        return quantize_amount(lower_ten)
    return quantize_amount(lower_ten + ROUNDING_STEP)


def round_signed_customer_price(value):
    amount = Decimal(str(value or 0))
    if amount < 0:
        return quantize_amount(round_customer_price(abs(amount)) * Decimal("-1"))
    return round_customer_price(amount)


def get_customer_gross_amount(net_amount):
    return round_signed_customer_price(Decimal(str(net_amount or 0)) * PRODUCT_VAT_MULTIPLIER)


def get_customer_sale_price(product):
    return round_customer_price(Decimal(str(product.sale_price or 0)) * PRODUCT_VAT_MULTIPLIER)


def get_retail_multiplier_code(name):
    for char in str(name or "").strip():
        if char.isalpha():
            return char.upper()
    return ""


def get_product_retail_multiplier_code(product):
    multiplier = product.retail_multiplier if product and product.retail_multiplier else None
    if multiplier:
        return get_retail_multiplier_code(multiplier.name)
    return ""


def get_multiplier_by_id(multiplier_id):
    if not multiplier_id:
        return None
    return db.session.get(RetailMultiplier, int(multiplier_id))


def sync_product_sale_price(product, multiplier_record=None):
    if multiplier_record is None and getattr(product, "retail_multiplier_id", None):
        multiplier_record = db.session.get(RetailMultiplier, int(product.retail_multiplier_id))
    elif multiplier_record is None and product.retail_multiplier:
        multiplier_record = product.retail_multiplier

    multiplier = multiplier_record.multiplier if multiplier_record else Decimal("1.00")
    product.sale_price = compute_sale_price(product.purchase_price, multiplier)


def get_available_barcodes(product):
    return [barcode for barcode in product.product_barcodes if barcode.status == "available"]


def sync_product_barcodes(product, desired_quantity):
    desired_quantity = max(int(desired_quantity or 0), 0)
    available_units = sorted(get_available_barcodes(product), key=lambda item: item.sequence_no)
    sold_units = sorted(
        [barcode for barcode in product.product_barcodes if barcode.status == "sold"],
        key=lambda item: item.sequence_no,
    )

    current_available = len(available_units)
    if desired_quantity < current_available:
        removable = current_available - desired_quantity
        for barcode in reversed(available_units[-removable:]):
            db.session.delete(barcode)
    elif desired_quantity > current_available:
        existing_sequences = {barcode.sequence_no for barcode in product.product_barcodes}
        next_sequence = 1
        create_count = desired_quantity - current_available
        created = 0
        while created < create_count:
            while next_sequence in existing_sequences:
                next_sequence += 1
            product_barcode = ProductBarcode(
                product=product,
                barcode=format_unit_barcode(product.product_code, next_sequence),
                sequence_no=next_sequence,
                status="available",
            )
            db.session.add(product_barcode)
            existing_sequences.add(next_sequence)
            created += 1
            next_sequence += 1

    product.stock_quantity = desired_quantity
    return sold_units


def reserve_barcodes_for_sale(product, sale_item, quantity, preferred_barcodes=None):
    preferred_barcodes = [value.strip() for value in (preferred_barcodes or []) if str(value).strip()]
    unique_barcodes = set(preferred_barcodes)
    if len(preferred_barcodes) != quantity or len(unique_barcodes) != quantity:
        raise ValueError(
            f"{product.name} için her adet adına tam birim barkodunu ayrı ayrı okutun."
        )

    allocated = (
        ProductBarcode.query.filter(
            ProductBarcode.product_id == product.id,
            ProductBarcode.barcode.in_(unique_barcodes),
            ProductBarcode.status == "available",
        )
        .with_for_update()
        .order_by(ProductBarcode.sequence_no.asc())
        .all()
    )
    if len(allocated) != quantity:
        raise ValueError(
            f"{product.name} için okutulan birim barkodlarından biri bulunamadı veya kullanılabilir değil."
        )

    for barcode in allocated:
        barcode.status = "sold"
        barcode.sale_item = sale_item

    product.stock_quantity = max(0, product.stock_quantity - quantity)
    return allocated


def release_barcodes_from_sale(sale_item, barcode_values):
    barcode_values = [value.strip() for value in (barcode_values or []) if str(value).strip()]
    if not barcode_values:
        return []

    barcodes = (
        ProductBarcode.query.filter(
            ProductBarcode.sale_item_id == sale_item.id,
            ProductBarcode.barcode.in_(barcode_values),
        )
        .order_by(ProductBarcode.sequence_no.asc())
        .all()
    )
    if len(barcodes) != len(set(barcode_values)):
        raise ValueError(f"{sale_item.product.name} için seçilen barkodlardan biri satış kaydında bulunamadı.")

    for barcode in barcodes:
        barcode.status = "available"
        barcode.sale_item = None

    sale_item.product.stock_quantity += len(barcodes)
    return barcodes
