from app.extensions import db
from app.utils import now_in_istanbul


class SystemSetting(db.Model):
    __tablename__ = "system_settings"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(500), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=now_in_istanbul,
        onupdate=now_in_istanbul,
    )


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    occurred_at = db.Column(db.DateTime, nullable=False, default=now_in_istanbul, index=True)
    actor_username = db.Column(db.String(120), nullable=True, index=True)
    event_type = db.Column(db.String(40), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    entity_type = db.Column(db.String(80), nullable=True, index=True)
    entity_id = db.Column(db.String(80), nullable=True, index=True)
    endpoint = db.Column(db.String(160), nullable=True)
    request_method = db.Column(db.String(12), nullable=True)
    status_code = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    details = db.Column(db.JSON, nullable=True)

    site = db.relationship("Site")
    store = db.relationship("Store")
    user = db.relationship("User")
