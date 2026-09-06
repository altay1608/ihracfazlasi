from decimal import Decimal

from app.extensions import db
from app.services.identity_access import get_active_site_id, get_active_store_id
from app.utils import now_in_istanbul


class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"

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
    transaction_code = db.Column(db.String(40), nullable=False, index=True)
    transaction_name = db.Column(db.String(140), nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False, default=now_in_istanbul, index=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_name = db.Column(db.String(150), nullable=False)
    product_code = db.Column(db.String(32), nullable=False, index=True)
    barcode_values = db.Column(db.String(500), nullable=True)
    quantity_delta = db.Column(db.Integer, nullable=False)
    quantity_before = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_cost = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    source_type = db.Column(db.String(40), nullable=False, index=True)
    source_id = db.Column(db.Integer, nullable=True, index=True)
    source_reference = db.Column(db.String(160), nullable=True)
    note = db.Column(db.Text, nullable=True)
    actor_username = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now_in_istanbul)

    product = db.relationship("Product", passive_deletes=True)
    site = db.relationship("Site")
    store = db.relationship("Store")
