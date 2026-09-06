from datetime import datetime

from sqlalchemy import UniqueConstraint

from app.extensions import db
from app.services.identity_access import get_active_site_id


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("site_id", "name", name="uq_categories_site_name"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, default=get_active_site_id, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    critical_stock_level = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Category {self.name}>"


class Variant(db.Model):
    __tablename__ = "variants"
    __table_args__ = (UniqueConstraint("site_id", "name", name="uq_variants_site_name"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, default=get_active_site_id, index=True)
    name = db.Column(db.String(50), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Variant {self.name}>"


class PaymentMethod(db.Model):
    __tablename__ = "payment_methods"
    __table_args__ = (UniqueConstraint("site_id", "name", name="uq_payment_methods_site_name"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, default=get_active_site_id, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<PaymentMethod {self.name}>"


class RetailMultiplier(db.Model):
    __tablename__ = "retail_multipliers"
    __table_args__ = (UniqueConstraint("site_id", "name", name="uq_retail_multipliers_site_name"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, default=get_active_site_id, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    multiplier = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    products = db.relationship("Product", back_populates="retail_multiplier", lazy="dynamic")

    def __repr__(self):
        return f"<RetailMultiplier {self.name}>"


class ReturnReason(db.Model):
    __tablename__ = "return_reasons"
    __table_args__ = (UniqueConstraint("site_id", "name", name="uq_return_reasons_site_name"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, default=get_active_site_id, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<ReturnReason {self.name}>"
