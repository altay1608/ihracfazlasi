from datetime import datetime
from app.extensions import db


class ReturnSettlement(db.Model):
    __tablename__ = 'return_settlements'
    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey('returns.id'), nullable=False, unique=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    credit_sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True, index=True)
    current_entry_id = db.Column(db.Integer, db.ForeignKey('current_entries.id'), nullable=True)
    credit_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    cash_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    payment_method = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (db.CheckConstraint('credit_amount >= 0', name='ck_return_credit_nonnegative'),)
