from datetime import datetime

from app.extensions import db
from app.services.identity_access import get_active_site_id, get_active_store_id
from app.models.document_sequence import register_document_number


class InventoryCount(db.Model):
    __tablename__ = "inventory_counts"
    __table_args__ = (
        db.UniqueConstraint("site_id", "document_no", name="uq_inventory_counts_site_document_no"),
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
    name = db.Column(db.String(160), nullable=False)
    category_filter = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)

    lines = db.relationship(
        "InventoryCountLine",
        back_populates="inventory_count",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InventoryCountLine.id.asc()",
    )
    site = db.relationship("Site")
    store = db.relationship("Store")

    scans = db.relationship(
        "InventoryCountScan",
        back_populates="inventory_count",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InventoryCountLine(db.Model):
    __tablename__ = "inventory_count_lines"

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
    inventory_count_id = db.Column(db.Integer, db.ForeignKey("inventory_counts.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    system_quantity = db.Column(db.Integer, nullable=False, default=0)
    counted_quantity = db.Column(db.Integer, nullable=False, default=0)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    inventory_count = db.relationship("InventoryCount", back_populates="lines")
    product = db.relationship("Product")
    scans = db.relationship(
        "InventoryCountScan",
        back_populates="line",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InventoryCountScan.scanned_at.asc()",
    )


class InventoryCountScan(db.Model):
    __tablename__ = "inventory_count_scans"
    __table_args__ = (
        db.UniqueConstraint(
            "inventory_count_id",
            "product_barcode_id",
            name="uq_inventory_count_scans_count_barcode",
        ),
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
    inventory_count_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_counts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inventory_count_line_id = db.Column(
        db.Integer,
        db.ForeignKey("inventory_count_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_barcode_id = db.Column(
        db.Integer,
        db.ForeignKey("product_barcodes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    barcode_value = db.Column(db.String(64), nullable=False)
    scanned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    inventory_count = db.relationship("InventoryCount", back_populates="scans")
    line = db.relationship("InventoryCountLine", back_populates="scans")
    product_barcode = db.relationship("ProductBarcode")


register_document_number(InventoryCount, "inventory_count")
