from datetime import datetime
from decimal import Decimal

from app.extensions import db
from app.services.identity_access import get_active_site_id, get_active_store_id
from app.models.document_sequence import register_document_number


class Return(db.Model):
    __tablename__ = "returns"
    __table_args__ = (
        db.UniqueConstraint("site_id", "document_no", name="uq_returns_site_document_no"),
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
    original_sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False, index=True)
    return_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    reason = db.Column(db.Text, nullable=False)
    note = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="tamamlandi")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    original_sale = db.relationship("Sale")
    site = db.relationship("Site")
    store = db.relationship("Store")
    items = db.relationship(
        "ReturnItem",
        back_populates="return_record",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<Return {self.document_no}>"

    @property
    def returned_line_references(self):
        references = {
            (item.original_sale_item.line_no, item.original_sale_item.release_no)
            for item in self.items
            if item.original_sale_item is not None and Decimal(item.refund_amount or 0) > 0
        }
        return [f"{line_no}.{release_no}" for line_no, release_no in sorted(references)]


class ReturnItem(db.Model):
    __tablename__ = "return_items"

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
    return_id = db.Column(db.Integer, db.ForeignKey("returns.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    original_sale_item_id = db.Column(
        db.Integer,
        db.ForeignKey("sale_items.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    quantity = db.Column(db.Integer, nullable=False)
    refund_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    gross_refund_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    unit_cost_snapshot = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    product_code_snapshot = db.Column(db.String(32), nullable=False)
    product_name_snapshot = db.Column(db.String(150), nullable=False)
    product_variant_snapshot = db.Column(db.String(120), nullable=True)

    return_record = db.relationship("Return", back_populates="items")
    product = db.relationship("Product", back_populates="return_items")
    original_sale_item = db.relationship("SaleItem", back_populates="return_items")

    @property
    def display_product_name(self):
        return self.product_name_snapshot or (
            self.original_sale_item.product_name_snapshot
            if self.original_sale_item is not None
            else self.product.name
        )

    @property
    def display_product_variant(self):
        return self.product_variant_snapshot

    @property
    def order_line_reference(self):
        if self.original_sale_item is None:
            return None
        return f"{self.original_sale_item.line_no}.{self.original_sale_item.release_no}"


register_document_number(Return, "return")
