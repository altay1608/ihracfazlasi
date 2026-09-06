from datetime import datetime

from sqlalchemy import UniqueConstraint

from app.extensions import db


package_features = db.Table(
    "package_features",
    db.Column("package_id", db.Integer, db.ForeignKey("packages.id", ondelete="CASCADE"), primary_key=True),
    db.Column("feature_id", db.Integer, db.ForeignKey("features.id", ondelete="CASCADE"), primary_key=True),
)


role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Package(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    max_stores = db.Column(db.Integer, nullable=False, default=1)
    max_users = db.Column(db.Integer, nullable=False, default=2)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    features = db.relationship("Feature", secondary=package_features, lazy="selectin")
    sites = db.relationship("Site", back_populates="package", lazy="dynamic")


class Feature(db.Model):
    __tablename__ = "features"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), nullable=False, unique=True, index=True)
    name = db.Column(db.String(140), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class Site(db.Model):
    __tablename__ = "sites"

    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False, unique=True, index=True)
    name = db.Column(db.String(160), nullable=False)
    is_sandbox = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    session_revision = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    package = db.relationship("Package", back_populates="sites")
    stores = db.relationship("Store", back_populates="site", cascade="all, delete-orphan", lazy="selectin")
    roles = db.relationship("Role", back_populates="site", cascade="all, delete-orphan", lazy="selectin")


class Store(db.Model):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("site_id", "code", name="uq_stores_site_code"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    site = db.relationship("Site", back_populates="stores")


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=True, index=True)
    feature_id = db.Column(db.Integer, db.ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(120), nullable=False, unique=True, index=True)
    name = db.Column(db.String(180), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    parent = db.relationship("Permission", remote_side=[id], backref=db.backref("children", lazy="selectin"))
    feature = db.relationship("Feature")


class Role(db.Model):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("site_id", "code", name="uq_roles_site_code"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(140), nullable=False)
    is_system_role = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    site = db.relationship("Site", back_populates="roles")
    permissions = db.relationship("Permission", secondary=role_permissions, lazy="selectin")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False, unique=True, index=True)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(180), nullable=True, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    must_change_password = db.Column(db.Boolean, nullable=False, default=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    two_factor_secret = db.Column(db.Text, nullable=True)
    two_factor_enabled = db.Column(db.Boolean, nullable=False, default=False)
    two_factor_confirmed_at = db.Column(db.DateTime, nullable=True)
    two_factor_recovery_codes = db.Column(db.Text, nullable=True)
    two_factor_last_counter = db.Column(db.BigInteger, nullable=True)
    is_platform_superadmin = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships = db.relationship("UserSiteRole", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    store_access = db.relationship("UserStoreAccess", back_populates="user", cascade="all, delete-orphan", lazy="selectin")


class UserSiteRole(db.Model):
    __tablename__ = "user_site_roles"
    __table_args__ = (UniqueConstraint("user_id", "site_id", name="uq_user_site_roles_user_site"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    all_stores = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    user = db.relationship("User", back_populates="memberships")
    site = db.relationship("Site")
    role = db.relationship("Role")


class UserStoreAccess(db.Model):
    __tablename__ = "user_store_access"
    __table_args__ = (UniqueConstraint("user_id", "store_id", name="uq_user_store_access_user_store"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)

    user = db.relationship("User", back_populates="store_access")
    store = db.relationship("Store")


class AuthThrottle(db.Model):
    """Shared login/MFA throttling state for multi-worker deployments."""
    __tablename__ = "auth_throttles"

    id = db.Column(db.Integer, primary_key=True)
    key_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    first_attempt_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    locked_until = db.Column(db.DateTime, nullable=True, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
