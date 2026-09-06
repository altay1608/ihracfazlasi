from datetime import datetime

from flask import has_request_context
from sqlalchemy import UniqueConstraint

from app.extensions import db
from app.services.identity_access import get_active_site_id, get_active_store_id


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("site_id", "barcode", name="uq_products_site_barcode"),
        UniqueConstraint("site_id", "product_code", name="uq_products_site_product_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(
        db.Integer,
        db.ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        default=get_active_site_id,
        index=True,
    )
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    barcode = db.Column(db.String(64), nullable=False, index=True)
    product_code = db.Column(db.String(32), nullable=False, index=True)
    purchase_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    sale_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    _legacy_stock_quantity = db.Column("stock_quantity", db.Integer, nullable=False, default=0)
    critical_stock_level = db.Column(db.Integer, nullable=True)
    variant = db.Column(db.String(120), nullable=True)
    retail_multiplier_id = db.Column(db.Integer, db.ForeignKey("retail_multipliers.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    sale_items = db.relationship("SaleItem", back_populates="product", lazy="dynamic")
    return_items = db.relationship("ReturnItem", back_populates="product", lazy="dynamic")
    retail_multiplier = db.relationship("RetailMultiplier", back_populates="products")
    site = db.relationship("Site")
    store_inventories = db.relationship(
        "StoreInventory",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    product_barcodes = db.relationship(
        "ProductBarcode",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductBarcode.sequence_no.asc()",
        lazy="selectin",
    )

    def _active_store_inventory(self, create=False):
        active_store_id = get_active_store_id()
        for inventory in self.store_inventories:
            if inventory.store_id == active_store_id:
                return inventory
        if not create:
            return None
        inventory = StoreInventory(
            site_id=self.site_id or get_active_site_id(),
            store_id=active_store_id,
            stock_quantity=0,
        )
        self.store_inventories.append(inventory)
        return inventory

    @property
    def stock_quantity(self):
        inventory = self._active_store_inventory()
        if inventory is not None:
            return int(inventory.stock_quantity or 0)
        if has_request_context():
            return 0
        return int(self._legacy_stock_quantity or 0)

    @stock_quantity.setter
    def stock_quantity(self, value):
        quantity = max(int(value or 0), 0)
        self._legacy_stock_quantity = quantity
        inventory = self._active_store_inventory(create=True)
        inventory.stock_quantity = quantity

    def __repr__(self):
        return f"<Product {self.name}>"


class ProductBarcode(db.Model):
    __tablename__ = "product_barcodes"
    __table_args__ = (
        UniqueConstraint("site_id", "barcode", name="uq_product_barcodes_site_barcode"),
        UniqueConstraint("product_id", "sequence_no", name="uq_product_barcodes_product_sequence"),
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
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    sale_item_id = db.Column(db.Integer, db.ForeignKey("sale_items.id"), nullable=True, index=True)
    barcode = db.Column(db.String(64), nullable=False, index=True)
    sequence_no = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="available", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    product = db.relationship("Product", back_populates="product_barcodes")
    sale_item = db.relationship("SaleItem", back_populates="product_barcodes")
    site = db.relationship("Site")
    store = db.relationship("Store")

    def __repr__(self):
        return f"<ProductBarcode {self.barcode}>"


class StoreInventory(db.Model):
    __tablename__ = "store_inventories"
    __table_args__ = (
        UniqueConstraint("store_id", "product_id", name="uq_store_inventories_store_product"),
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
        db.ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        default=get_active_store_id,
        index=True,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    critical_stock_level = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    site = db.relationship("Site")
    store = db.relationship("Store")
    product = db.relationship("Product", back_populates="store_inventories")
