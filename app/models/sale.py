from datetime import datetime
from decimal import Decimal

from sqlalchemy import event, func, select

from app.extensions import db
from app.services.identity_access import get_active_site_id, get_active_store_id
from app.models.document_sequence import register_document_number
from app.utils import quantize_amount


class Sale(db.Model):
    __tablename__ = "sales"
    __table_args__ = (
        db.UniqueConstraint("site_id", "document_no", name="uq_sales_site_document_no"),
    )

    id = db.Column(db.Integer, primary_key=True)
    document_no = db.Column(db.Integer, nullable=False, index=True)
    site_id = db.Column(
        db.Integer,
        db.ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        default=get_active_site_id,
        index=True,
    )
    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
        default=get_active_store_id,
        index=True,
    )
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_discount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    order_status = db.Column(db.String(30), nullable=False, default="DELIVERED", index=True)
    payment_status = db.Column(db.String(30), nullable=False, default="PAID", index=True)
    currency_code = db.Column(db.String(3), nullable=False, default="TRY")
    revision_no = db.Column(db.Integer, nullable=False, default=1)
    payment_method = db.Column(db.String(30), nullable=False)
    customer_name = db.Column(db.String(150), nullable=True)
    customer_phone = db.Column(db.String(40), nullable=True)
    customer_mobile = db.Column(db.String(40), nullable=True)
    customer_email = db.Column(db.String(150), nullable=True)
    customer_city = db.Column(db.String(120), nullable=True)
    customer_address = db.Column(db.Text, nullable=True)
    customer_tax_office = db.Column(db.String(120), nullable=True)
    customer_tax_number = db.Column(db.String(40), nullable=True)
    customer_note = db.Column(db.String(200), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    items = db.relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SaleItem.line_no.asc()",
    )
    site = db.relationship("Site")
    store = db.relationship("Store")

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items)

    @property
    def order_no(self):
        return self.document_no

    @property
    def order_date(self):
        return self.sale_date

    @property
    def lines(self):
        return self.items

    @property
    def status_label(self):
        return {
            "DELIVERED": "Teslim Edildi",
            "PARTIALLY_RETURNED": "Kısmi İade",
            "RETURNED": "İade Edildi",
            "CANCELLED": "İptal Edildi",
        }.get(self.order_status, self.order_status)

    @property
    def payment_status_label(self):
        return {
            "PAID": "Ödendi",
            "PARTIALLY_REFUNDED": "Kısmi Geri Ödeme",
            "REFUNDED": "Geri Ödendi",
            "VOIDED": "İptal Edildi",
        }.get(self.payment_status, self.payment_status)

    def __repr__(self):
        return f"<Sale {self.document_no}>"


class SaleItem(db.Model):
    __tablename__ = "sale_items"
    __table_args__ = (
        db.UniqueConstraint("sale_id", "line_no", "release_no", name="uq_sale_items_order_line_release"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(
        db.Integer,
        db.ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        default=get_active_site_id,
        index=True,
    )
    store_id = db.Column(
        db.Integer,
        db.ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
        default=get_active_store_id,
        index=True,
    )
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    line_no = db.Column(db.Integer, nullable=False)
    release_no = db.Column(db.Integer, nullable=False, default=1)
    line_status = db.Column(db.String(30), nullable=False, default="DELIVERED", index=True)
    quantity = db.Column(db.Integer, nullable=False)
    delivered_quantity = db.Column(db.Integer, nullable=False, default=0)
    returned_quantity = db.Column(db.Integer, nullable=False, default=0)
    cancelled_quantity = db.Column(db.Integer, nullable=False, default=0)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    header_discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    rounding_adjustment_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    vat_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("10.00"))
    unit_cost_snapshot = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    product_code_snapshot = db.Column(db.String(32), nullable=False)
    product_name_snapshot = db.Column(db.String(150), nullable=False)
    product_variant_snapshot = db.Column(db.String(120), nullable=True)
    product_category_snapshot = db.Column(db.String(100), nullable=False)

    sale = db.relationship("Sale", back_populates="items")
    product = db.relationship("Product", back_populates="sale_items")
    product_barcodes = db.relationship("ProductBarcode", back_populates="sale_item", lazy="selectin")
    return_items = db.relationship("ReturnItem", back_populates="original_sale_item", lazy="selectin")

    @property
    def line_total(self):
        return (self.unit_price * self.quantity) - self.discount_amount

    @property
    def ordered_quantity(self):
        return self.quantity

    @property
    def open_quantity(self):
        return max(
            int(self.quantity or 0)
            - int(self.delivered_quantity or 0)
            - int(self.cancelled_quantity or 0),
            0,
        )

    @property
    def net_amount(self):
        return (
            (self.unit_price * self.quantity)
            - self.discount_amount
            - self.header_discount_amount
        )

    @property
    def gross_amount(self):
        return quantize_amount(
            self.net_amount * (Decimal("1.00") + (self.vat_rate / Decimal("100")))
        ) + self.rounding_adjustment_amount

    @property
    def gross_discount_amount(self):
        net_discount = self.discount_amount + self.header_discount_amount
        return quantize_amount(
            net_discount * (Decimal("1.00") + (self.vat_rate / Decimal("100")))
        )

    @property
    def status_label(self):
        return {
            "DELIVERED": "Teslim Edildi",
            "PARTIALLY_RETURNED": "Kısmi İade",
            "RETURNED": "İade Edildi",
            "CANCELLED": "İptal Edildi",
        }.get(self.line_status, self.line_status)


register_document_number(Sale, "sale")


@event.listens_for(SaleItem, "before_insert")
def fill_customer_order_line_defaults(_mapper, connection, line):
    """Keep direct model inserts compatible while routes provide richer snapshots."""
    if line.line_no is None:
        current_line_no = connection.execute(
            select(func.max(SaleItem.__table__.c.line_no)).where(
                SaleItem.__table__.c.sale_id == line.sale_id
            )
        ).scalar()
        line.line_no = int(current_line_no or 0) + 1
    line.release_no = int(line.release_no or 1)
    line.delivered_quantity = int(
        line.delivered_quantity if line.delivered_quantity is not None else line.quantity or 0
    )
    line.returned_quantity = int(line.returned_quantity or 0)
    line.cancelled_quantity = int(line.cancelled_quantity or 0)

    product = line.product
    if product is not None:
        line.product_code_snapshot = line.product_code_snapshot or product.product_code
        line.product_name_snapshot = line.product_name_snapshot or product.name
        line.product_variant_snapshot = line.product_variant_snapshot or product.variant
        line.product_category_snapshot = line.product_category_snapshot or product.category
        if line.unit_cost_snapshot is None:
            line.unit_cost_snapshot = product.purchase_price

# Domain aliases keep the existing table and foreign keys stable during the
# customer-order migration while new code can use explicit business names.
CustomerOrder = Sale
CustomerOrderLine = SaleItem
