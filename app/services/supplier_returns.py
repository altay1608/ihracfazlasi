from datetime import datetime
from decimal import Decimal
from uuid import UUID
from app.extensions import db
from app.models import Product, ProductBarcode, StoreInventory, CurrentAccount, CurrentEntry, SupplierReturn
from app.services.finance import _require_activation, _account, _category, _append_movement, ensure_finance_period_open
from app.services.inventory_history import record_inventory_movement
from app.utils import quantize_amount


def create_supplier_return(*, site_id, store_id, supplier_id, product_id, quantity, amount,
                           mode, reason, request_key, current_entry_id=None, account_id=None, barcodes=None):
    request_key = str(UUID(str(request_key)))
    _require_activation(site_id, store_id)
    # Serialize submissions for this supplier, including duplicate HTTP requests.
    supplier = CurrentAccount.query.filter_by(id=supplier_id, site_id=site_id,
        account_category="supplier", is_active=True).with_for_update().one_or_none()
    if not supplier:
        raise ValueError("Geçerli bir toptancı seçin.")
    existing = SupplierReturn.query.filter_by(site_id=site_id, store_id=store_id, request_key=request_key).first()
    if existing:
        return existing
    when = datetime.utcnow()
    ensure_finance_period_open(site_id, store_id, when)
    amount = quantize_amount(Decimal(str(amount)))
    reason = str(reason or "").strip()
    if not amount.is_finite() or amount <= 0 or not 1 <= quantity <= 999 or not 5 <= len(reason) <= 500:
        raise ValueError("Pozitif tutar/adet ve en az 5 karakter açıklama girin.")
    if mode not in {"debt", "refund"}:
        raise ValueError("Borçtan düş veya para iadesi seçin.")
    entry = None
    account = None
    if mode == "debt":
        entry = CurrentEntry.query.filter_by(id=current_entry_id, site_id=site_id, store_id=store_id,
            current_account_id=supplier_id, entry_type="payable").with_for_update().one_or_none()
        if not entry or amount > entry.remaining_amount:
            raise ValueError("İade tutarı seçilen toptancı borcunun kalanını aşamaz.")
    else:
        account = _account(site_id, store_id, account_id)
        if account.account_type not in {"cash", "bank"}:
            raise ValueError("Para iadesi için nakit veya banka hesabı seçin.")
    product = Product.query.filter_by(id=product_id, site_id=site_id).with_for_update().one_or_none()
    inventory = StoreInventory.query.filter_by(site_id=site_id, store_id=store_id,
        product_id=product_id).with_for_update().one_or_none()
    if not product or not inventory or inventory.stock_quantity < quantity:
        raise ValueError("Bu mağazada yeterli ürün stoğu yok.")
    codes = list(dict.fromkeys(str(value).strip() for value in (barcodes or []) if str(value).strip()))
    selected = []
    if product.barcode_mode != "shared":
        selected = ProductBarcode.query.filter_by(site_id=site_id, store_id=store_id,
            product_id=product_id, status="available").filter(ProductBarcode.barcode.in_(codes)).with_for_update().all()
        if len(codes) != quantity or len(selected) != quantity:
            raise ValueError("İade edilecek her adedin tam birim barkodunu girin.")
    row = SupplierReturn(site_id=site_id, store_id=store_id, supplier_id=supplier_id,
        product_id=product_id, product_name=product.name, quantity=quantity, amount=amount,
        mode=mode, current_entry_id=entry.id if entry else None, reason=reason,
        request_key=request_key, barcode_values="\n".join(codes))
    db.session.add(row)
    db.session.flush()
    before = inventory.stock_quantity
    inventory.stock_quantity -= quantity
    for barcode in selected:
        barcode.status = "supplier_returned"
    if entry:
        entry.remaining_amount = quantize_amount(entry.remaining_amount - amount)
        entry.status = "closed" if entry.remaining_amount == 0 else "partial"
    else:
        movement = _append_movement(site_id=site_id, store_id=store_id, account=account,
            category=_category(site_id, "CURRENT"), direction="in", amount=amount, occurred_at=when,
            movement_type="supplier_return", source_type="supplier_return", source_id=row.id,
            source_key=f"supplier-return:{row.id}", pair_key=f"supplier-return:{row.id}", description=f"Toptancı iadesi: {product.name}",
            current_account_id=supplier_id, is_overhead=False)
        row.movement_id = movement.id
    history = record_inventory_movement(product, transaction_type="supplier_return_out",
        quantity_before=before, quantity_after=inventory.stock_quantity, source_type="supplier_return",
        source_id=row.id, source_reference=f"Toptancı iadesi #{row.id}", barcode_values=codes, note=reason)
    history.site_id, history.store_id = site_id, store_id
    return row
