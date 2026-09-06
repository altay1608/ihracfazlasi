from __future__ import annotations

from decimal import Decimal

from flask import has_request_context, session

from app.extensions import db
from app.models import InventoryTransaction
from app.utils import quantize_amount


TRANSACTION_TYPES = {
    "opening_balance": ("OPENING-BAL", "Başlangıç Stok Devri"),
    "product_opening": ("PRODUCT-REC", "Ürün Kartı Açılış Stoğu"),
    "manual_in": ("MANUAL-ADD", "Manuel Stok Artışı"),
    "manual_out": ("MANUAL-REM", "Manuel Stok Azalışı"),
    "import_opening": ("IMPORT-REC", "Excel Açılış Stok Girişi"),
    "sale_out": ("SALE-OUT", "Satış Çıkışı"),
    "sale_update_in": ("SALE-REV", "Satış Düzenleme Girişi"),
    "sale_update_out": ("SALE-ADJ", "Satış Düzenleme Çıkışı"),
    "return_in": ("RETURN-REC", "İade Stok Girişi"),
    "exchange_out": ("EXCHANGE-OUT", "Değişim Stok Çıkışı"),
    "count_in": ("COUNT-ADD", "Sayım Fazlası Stok Girişi"),
    "count_out": ("COUNT-REM", "Sayım Eksiği Stok Çıkışı"),
    "product_delete": ("PRODUCT-REM", "Ürün Kartı Silme Çıkışı"),
}


def get_transaction_type(key: str) -> tuple[str, str]:
    try:
        return TRANSACTION_TYPES[key]
    except KeyError as exc:
        raise ValueError(f"Bilinmeyen stok işlem türü: {key}") from exc


def record_inventory_movement(
    product,
    *,
    transaction_type: str,
    quantity_before: int,
    quantity_after: int,
    source_type: str,
    source_id: int | None = None,
    source_reference: str | None = None,
    barcode_values: list[str] | None = None,
    note: str | None = None,
):
    before = int(quantity_before or 0)
    after = int(quantity_after or 0)
    quantity_delta = after - before
    if quantity_delta == 0:
        return None

    transaction_code, transaction_name = get_transaction_type(transaction_type)
    unit_cost = quantize_amount(Decimal(str(product.purchase_price or 0)))
    values = [str(value).strip() for value in (barcode_values or []) if str(value).strip()]
    barcode_summary = ", ".join(values) or None
    if barcode_summary and len(barcode_summary) > 500:
        barcode_summary = barcode_summary[:497] + "..."

    transaction = InventoryTransaction(
        transaction_code=transaction_code,
        transaction_name=transaction_name,
        product=product,
        product_name=product.name,
        product_code=product.product_code,
        barcode_values=barcode_summary,
        quantity_delta=quantity_delta,
        quantity_before=before,
        quantity_after=after,
        unit_cost=unit_cost,
        total_cost=quantize_amount(abs(quantity_delta) * unit_cost),
        source_type=source_type,
        source_id=source_id,
        source_reference=source_reference,
        note=note,
        actor_username=session.get("auth_user") if has_request_context() else None,
    )
    db.session.add(transaction)
    return transaction
