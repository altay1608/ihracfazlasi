from datetime import datetime
from app.extensions import db


class SupplierReturn(db.Model):
    __tablename__ = "supplier_returns"
    __table_args__ = (db.UniqueConstraint("site_id", "store_id", "request_key", name="uq_supplier_return_request"),
                     db.CheckConstraint("quantity > 0 AND amount > 0", name="ck_supplier_return_positive"))
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("current_accounts.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    mode = db.Column(db.String(20), nullable=False)
    current_entry_id = db.Column(db.Integer, db.ForeignKey("current_entries.id"))
    movement_id = db.Column(db.Integer, db.ForeignKey("finance_movements.id"))
    barcode_values = db.Column(db.Text, nullable=False, default="")
    reason = db.Column(db.String(500), nullable=False)
    request_key = db.Column(db.String(36), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    supplier = db.relationship("CurrentAccount")
