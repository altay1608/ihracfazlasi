import re
from secrets import compare_digest

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (
    Category,
    Feature,
    Package,
    PaymentMethod,
    Permission,
    RetailMultiplier,
    ReturnReason,
    Role,
    Site,
    Store,
    User,
    UserSiteRole,
    UserStoreAccess,
    Variant,
)
from app.security_catalog import CUSTOMER_REPRESENTATIVE_PERMISSIONS
from app.services.access_control import platform_admin_required
from app.services.audit_trail import persist_audit_event
from app.services.password_policy import password_is_strong
from app.services.two_factor import reset_two_factor
from app.services.reference_data import (
    DEFAULT_CATEGORIES,
    DEFAULT_PAYMENT_METHODS,
    DEFAULT_RETAIL_MULTIPLIERS,
    DEFAULT_RETURN_REASONS,
    DEFAULT_VARIANTS,
)
from app.services.tenant_scope import platform_site_provisioning_scope


bp = Blueprint("platform", __name__, url_prefix="/platform")
USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,60}$")
SITE_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,19}$")
STORE_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,29}$")


def _csrf_is_valid():
    expected = session.get("auth_csrf_token", "")
    submitted = request.form.get("csrf_token", "")
    return bool(expected) and compare_digest(str(expected), str(submitted))


def _site_or_404(site_id):
    return db.get_or_404(Site, site_id)


def _store_or_404(site_id, store_id):
    return Store.query.filter_by(id=store_id, site_id=site_id).first_or_404()


def _site_memberships(site_id):
    return (
        UserSiteRole.query.filter_by(site_id=site_id)
        .join(User, User.id == UserSiteRole.user_id)
        .order_by(User.full_name.asc(), User.username.asc())
        .all()
    )


def _permissions_for_package(package):
    feature_ids = {feature.id for feature in package.features}
    if not feature_ids:
        return []
    return (
        Permission.query.filter(
            Permission.feature_id.in_(feature_ids),
            ~Permission.code.startswith("platform."),
        )
        .order_by(Permission.sort_order.asc(), Permission.id.asc())
        .all()
    )


def _package_permissions(site):
    return _permissions_for_package(site.package)


def _permission_groups(site):
    grouped = []
    package_feature_ids = {feature.id for feature in site.package.features}
    permissions = (
        Permission.query.filter(~Permission.code.startswith("platform."))
        .order_by(Permission.sort_order.asc(), Permission.id.asc())
        .all()
    )
    features = (
        Feature.query.filter(Feature.code != "platform")
        .order_by(Feature.sort_order.asc(), Feature.id.asc())
        .all()
    )
    for feature in features:
        feature_permissions = [item for item in permissions if item.feature_id == feature.id]
        if feature_permissions:
            grouped.append((feature, feature_permissions, feature.id in package_feature_ids))
    return grouped


def _active_packages():
    return Package.query.filter_by(is_active=True).order_by(Package.id.asc()).all()


def _active_store_count(site_id, *, exclude_store_id=None):
    query = Store.query.filter_by(site_id=site_id, is_active=True)
    if exclude_store_id is not None:
        query = query.filter(Store.id != exclude_store_id)
    return query.count()


def _active_user_count(site_id, *, exclude_user_id=None):
    query = (
        UserSiteRole.query.join(User, User.id == UserSiteRole.user_id)
        .filter(
            UserSiteRole.site_id == site_id,
            UserSiteRole.is_active.is_(True),
            User.is_active.is_(True),
        )
    )
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.count()


def _store_limit_reached(site, *, exclude_store_id=None):
    return _active_store_count(site.id, exclude_store_id=exclude_store_id) >= int(site.package.max_stores)


def _user_limit_reached(site, *, exclude_user_id=None):
    return _active_user_count(site.id, exclude_user_id=exclude_user_id) >= int(site.package.max_users)


def _validate_store_form(site, store=None):
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    is_active = request.form.get("is_active") == "1"
    errors = []

    if len(name) < 2 or len(name) > 160:
        errors.append("Mağaza adı 2-160 karakter arasında olmalıdır.")
    if not STORE_CODE_PATTERN.fullmatch(code):
        errors.append("Mağaza kodu 2-30 karakter olmalı; yalnız büyük harf, rakam ve tire içermelidir.")
    else:
        duplicate_query = Store.query.filter(
            Store.site_id == site.id,
            func.lower(Store.code) == code.casefold(),
        )
        if store is not None:
            duplicate_query = duplicate_query.filter(Store.id != store.id)
        if duplicate_query.first():
            errors.append("Bu mağaza kodu aynı site içinde kullanımda.")

    if store is not None and store.is_active and not is_active:
        other_active_store = Store.query.filter(
            Store.site_id == site.id,
            Store.id != store.id,
            Store.is_active.is_(True),
        ).first()
        if other_active_store is None:
            errors.append("Sitenin son aktif mağazası pasife alınamaz.")

    return errors, {"name": name, "code": code, "is_active": is_active}


def _seed_site_reference_data(site_id):
    for name, description in DEFAULT_CATEGORIES:
        db.session.add(Category(site_id=site_id, name=name, description=description, is_active=True))
    for name in DEFAULT_VARIANTS:
        db.session.add(Variant(site_id=site_id, name=name, is_active=True))
    for name, is_active in DEFAULT_PAYMENT_METHODS:
        db.session.add(PaymentMethod(site_id=site_id, name=name, is_active=is_active))
    for name in DEFAULT_RETURN_REASONS:
        db.session.add(ReturnReason(site_id=site_id, name=name, is_active=True))
    for name, multiplier, is_default in DEFAULT_RETAIL_MULTIPLIERS:
        db.session.add(
            RetailMultiplier(
                site_id=site_id,
                name=name,
                multiplier=multiplier,
                is_active=True,
                is_default=is_default,
            )
        )


def _create_site_roles(site, package):
    all_site_permissions = (
        Permission.query.filter(~Permission.code.startswith("platform."))
        .order_by(Permission.sort_order.asc(), Permission.id.asc())
        .all()
    )
    owner = Role(
        site=site,
        code="OWNER_MANAGER",
        name="Mağaza Yöneticisi / Sahip",
        is_system_role=True,
        is_active=True,
        permissions=list(all_site_permissions),
    )
    representative = Role(
        site=site,
        code="CUSTOMER_REPRESENTATIVE",
        name="Mağaza Müşteri Temsilcisi",
        is_system_role=True,
        is_active=True,
        permissions=[
            permission
            for permission in all_site_permissions
            if permission.code in CUSTOMER_REPRESENTATIVE_PERMISSIONS
        ],
    )
    db.session.add_all([owner, representative])


def _form_user_values(site, user=None, membership=None):
    return {
        "user": user,
        "membership": membership,
        "roles": Role.query.filter_by(site_id=site.id, is_active=True).order_by(Role.name.asc()).all(),
        "stores": Store.query.filter_by(site_id=site.id, is_active=True).order_by(Store.name.asc()).all(),
        "site": site,
    }


def _validate_user_form(site, user=None):
    username = request.form.get("username", "").strip().casefold()
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().casefold() or None
    password = request.form.get("temporary_password", "")
    confirm_password = request.form.get("confirm_password", "")
    role_id = request.form.get("role_id", type=int)
    all_stores = request.form.get("all_stores") == "1"
    store_ids = {int(item) for item in request.form.getlist("store_ids") if item.isdigit()}

    errors = []
    if not USERNAME_PATTERN.fullmatch(username):
        errors.append("Kullanıcı adı 3-60 karakter olmalı; yalnız küçük harf, rakam, nokta, tire ve alt çizgi içerebilir.")
    if len(full_name) < 2 or len(full_name) > 160:
        errors.append("Ad soyad 2-160 karakter arasında olmalıdır.")
    if email and ("@" not in email or len(email) > 180):
        errors.append("Geçerli bir e-posta adresi girin.")

    username_query = User.query.filter(func.lower(User.username) == username)
    if user is not None:
        username_query = username_query.filter(User.id != user.id)
    if username_query.first():
        errors.append("Bu kullanıcı adı kullanımda.")
    if email:
        email_query = User.query.filter(func.lower(User.email) == email)
        if user is not None:
            email_query = email_query.filter(User.id != user.id)
        if email_query.first():
            errors.append("Bu e-posta adresi kullanımda.")

    role = db.session.get(Role, role_id) if role_id else None
    if role is None or role.site_id != site.id or not role.is_active:
        errors.append("Geçerli bir site rolü seçin.")

    allowed_store_ids = {
        store.id for store in Store.query.filter_by(site_id=site.id, is_active=True).all()
    }
    if not all_stores and not store_ids:
        errors.append("En az bir mağaza seçin veya tüm mağazalara erişim verin.")
    if not store_ids <= allowed_store_ids:
        errors.append("Başka bir siteye ait mağaza seçilemez.")

    password_required = user is None
    if password_required or password:
        if not password_is_strong(password):
            errors.append("Geçici şifre en az 10 karakter olmalı; büyük harf, küçük harf ve rakam içermelidir.")
        elif password != confirm_password:
            errors.append("Geçici şifre tekrarı eşleşmiyor.")

    return errors, {
        "username": username,
        "full_name": full_name,
        "email": email,
        "password": password,
        "role": role,
        "all_stores": all_stores,
        "store_ids": store_ids,
        "is_active": request.form.get("is_active") == "1",
        "reset_two_factor": request.form.get("reset_two_factor") == "1",
    }


def _apply_store_access(user, membership, store_ids):
    membership.all_stores = bool(membership.all_stores)
    site_store_ids = [store.id for store in Store.query.filter_by(site_id=membership.site_id).all()]
    if site_store_ids:
        UserStoreAccess.query.filter(
            UserStoreAccess.user_id == user.id,
            UserStoreAccess.store_id.in_(site_store_ids),
        ).delete(synchronize_session=False)
    if membership.all_stores:
        return
    for store_id in sorted(store_ids):
        db.session.add(UserStoreAccess(user_id=user.id, store_id=store_id))


@bp.route("/")
@platform_admin_required
def index():
    sites = Site.query.order_by(Site.is_sandbox.desc(), Site.code.asc()).all()
    membership_counts = dict(
        db.session.query(UserSiteRole.site_id, func.count(UserSiteRole.id))
        .filter(UserSiteRole.is_active.is_(True))
        .group_by(UserSiteRole.site_id)
        .all()
    )
    return render_template(
        "platform/index.html",
        sites=sites,
        membership_counts=membership_counts,
    )


@bp.route("/sites/new", methods=["GET", "POST"])
@platform_admin_required
def create_site():
    packages = _active_packages()
    if request.method == "POST":
        site_name = request.form.get("site_name", "").strip()
        site_code = request.form.get("site_code", "").strip().upper()
        store_name = request.form.get("store_name", "").strip()
        store_code = request.form.get("store_code", "").strip().upper()
        package_id = request.form.get("package_id", type=int)
        package = db.session.get(Package, package_id) if package_id else None
        errors = []

        if not _csrf_is_valid():
            errors.append("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.")
        if len(site_name) < 2 or len(site_name) > 160:
            errors.append("Site adı 2-160 karakter arasında olmalıdır.")
        if not SITE_CODE_PATTERN.fullmatch(site_code):
            errors.append("Site kodu 2-20 karakter olmalı; yalnız büyük harf, rakam ve tire içermelidir.")
        elif Site.query.filter(func.lower(Site.code) == site_code.casefold()).first():
            errors.append("Bu site kodu kullanımda.")
        if package is None or not package.is_active:
            errors.append("Aktif bir paket seçin.")
        elif not package.features:
            errors.append("Bu paketin kapsamı henüz tanımlanmadı; siteye atanamaz.")
        if len(store_name) < 2 or len(store_name) > 160:
            errors.append("İlk mağaza adı 2-160 karakter arasında olmalıdır.")
        if not STORE_CODE_PATTERN.fullmatch(store_code):
            errors.append("Mağaza kodu 2-30 karakter olmalı; yalnız büyük harf, rakam ve tire içermelidir.")

        if not errors:
            try:
                with platform_site_provisioning_scope():
                    site = Site(
                        code=site_code,
                        name=site_name,
                        package=package,
                        is_sandbox=False,
                        is_active=True,
                    )
                    db.session.add(site)
                    db.session.flush()
                    db.session.add(Store(site=site, code=store_code, name=store_name, is_active=True))
                    _create_site_roles(site, package)
                    _seed_site_reference_data(site.id)
                    db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors.append("Site veya mağaza kodu kullanımda; kayıt oluşturulmadı.")
            else:
                persist_audit_event(
                    "PLATFORM_SITE_CREATED",
                    event_type="security",
                    entity_type="site",
                    entity_id=str(site.id),
                    details={"site": site.code, "package": package.code, "store": store_code},
                )
                flash(f"{site.name} sitesi ve {store_name} mağazası oluşturuldu.", "success")
                return redirect(url_for("platform.site_detail", site_id=site.id))

        for error in errors:
            flash(error, "error")

    return render_template(
        "platform/site_form.html",
        packages=packages,
        form_data=request.form,
    )


@bp.route("/sites/<int:site_id>")
@platform_admin_required
def site_detail(site_id):
    site = _site_or_404(site_id)
    roles = Role.query.filter_by(site_id=site.id).order_by(Role.name.asc()).all()
    roles.sort(key=lambda role: (role.code != "OWNER_MANAGER", role.name))
    stores = Store.query.filter_by(site_id=site.id).order_by(Store.is_active.desc(), Store.name.asc()).all()
    memberships = _site_memberships(site.id)
    package_feature_ids = {feature.id for feature in site.package.features}
    effective_role_counts = {
        role.id: sum(
            1
            for permission in role.permissions
            if permission.feature_id in package_feature_ids
        )
        for role in roles
    }
    return render_template(
        "platform/site_detail.html",
        site=site,
        stores=stores,
        memberships=memberships,
        roles=roles,
        permission_groups=_permission_groups(site),
        effective_role_counts=effective_role_counts,
        packages=_active_packages(),
        active_store_count=_active_store_count(site.id),
        active_user_count=_active_user_count(site.id),
    )


@bp.route("/sites/<int:site_id>/package", methods=["POST"])
@platform_admin_required
def update_site_package(site_id):
    site = _site_or_404(site_id)
    if not _csrf_is_valid():
        flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        return redirect(url_for("platform.site_detail", site_id=site.id))

    package_id = request.form.get("package_id", type=int)
    package = db.session.get(Package, package_id) if package_id else None
    errors = []
    active_store_count = _active_store_count(site.id)
    active_user_count = _active_user_count(site.id)

    if package is None or not package.is_active:
        errors.append("Aktif bir paket seçin.")
    elif not package.features:
        errors.append("Bu paketin kapsamı henüz tanımlanmadı; siteye atanamaz.")
    else:
        if active_store_count > int(package.max_stores):
            errors.append(
                f"{package.name} paketi en fazla {package.max_stores} aktif mağazaya izin verir; "
                f"bu sitede {active_store_count} aktif mağaza var."
            )
        if active_user_count > int(package.max_users):
            errors.append(
                f"{package.name} paketi en fazla {package.max_users} aktif kullanıcıya izin verir; "
                f"bu sitede {active_user_count} aktif kullanıcı var."
            )

    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(url_for("platform.site_detail", site_id=site.id))

    if site.package_id == package.id:
        flash(f"{site.name} zaten {package.name} paketini kullanıyor.", "info")
        return redirect(url_for("platform.site_detail", site_id=site.id))

    previous_package = site.package
    site.package = package
    site.session_revision = int(site.session_revision or 1) + 1
    db.session.commit()
    persist_audit_event(
        "PLATFORM_SITE_PACKAGE_UPDATED",
        event_type="security",
        entity_type="site",
        entity_id=str(site.id),
        details={
            "site": site.code,
            "previous_package": previous_package.code,
            "package": package.code,
            "session_revision": site.session_revision,
            "active_stores": active_store_count,
            "active_users": active_user_count,
        },
    )
    flash(f"{site.name} sitesi {package.name} paketine geçirildi.", "success")
    return redirect(url_for("platform.site_detail", site_id=site.id))


@bp.route("/sites/<int:site_id>/stores/new", methods=["GET", "POST"])
@platform_admin_required
def create_store(site_id):
    site = _site_or_404(site_id)
    if request.method == "POST":
        if not _csrf_is_valid():
            flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        else:
            errors, values = _validate_store_form(site)
            if values["is_active"] and _store_limit_reached(site):
                errors.append(
                    f"{site.package.name} paketinde en fazla {site.package.max_stores} aktif mağaza kullanılabilir."
                )
            if not errors:
                store = Store(
                    site_id=site.id,
                    name=values["name"],
                    code=values["code"],
                    is_active=values["is_active"],
                )
                db.session.add(store)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    errors.append("Bu mağaza kodu aynı site içinde kullanımda.")
                else:
                    persist_audit_event(
                        "PLATFORM_STORE_CREATED",
                        event_type="security",
                        entity_type="store",
                        entity_id=str(store.id),
                        details={"site": site.code, "store": store.code},
                    )
                    flash(f"{store.name} mağazası oluşturuldu.", "success")
                    return redirect(url_for("platform.site_detail", site_id=site.id))
            for error in errors:
                flash(error, "error")
    return render_template(
        "platform/store_form.html",
        site=site,
        store=None,
        form_data=request.form,
    )


@bp.route("/sites/<int:site_id>/stores/<int:store_id>/edit", methods=["GET", "POST"])
@platform_admin_required
def edit_store(site_id, store_id):
    site = _site_or_404(site_id)
    store = _store_or_404(site.id, store_id)
    if request.method == "POST":
        if not _csrf_is_valid():
            flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        else:
            errors, values = _validate_store_form(site, store=store)
            if values["is_active"] and _store_limit_reached(site, exclude_store_id=store.id):
                errors.append(
                    f"{site.package.name} paketinde en fazla {site.package.max_stores} aktif mağaza kullanılabilir."
                )
            if not errors:
                store.name = values["name"]
                store.code = values["code"]
                store.is_active = values["is_active"]
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    errors.append("Bu mağaza kodu aynı site içinde kullanımda.")
                else:
                    persist_audit_event(
                        "PLATFORM_STORE_UPDATED",
                        event_type="security",
                        entity_type="store",
                        entity_id=str(store.id),
                        details={"site": site.code, "store": store.code, "is_active": store.is_active},
                    )
                    flash(f"{store.name} mağazası güncellendi.", "success")
                    return redirect(url_for("platform.site_detail", site_id=site.id))
            for error in errors:
                flash(error, "error")
    return render_template(
        "platform/store_form.html",
        site=site,
        store=store,
        form_data=request.form,
    )


@bp.route("/sites/<int:site_id>/users/new", methods=["GET", "POST"])
@platform_admin_required
def create_user(site_id):
    site = _site_or_404(site_id)
    if request.method == "POST":
        if not _csrf_is_valid():
            flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        else:
            errors, values = _validate_user_form(site)
            if values["is_active"] and _user_limit_reached(site):
                errors.append(
                    f"{site.package.name} paketinde en fazla {site.package.max_users} aktif kullanıcı kullanılabilir."
                )
            if not errors:
                user = User(
                    username=values["username"],
                    full_name=values["full_name"],
                    email=values["email"],
                    password_hash=generate_password_hash(values["password"]),
                    must_change_password=True,
                    is_platform_superadmin=False,
                    is_active=values["is_active"],
                )
                db.session.add(user)
                db.session.flush()
                membership = UserSiteRole(
                    user_id=user.id,
                    site_id=site.id,
                    role_id=values["role"].id,
                    all_stores=values["all_stores"],
                    is_active=True,
                )
                db.session.add(membership)
                db.session.flush()
                _apply_store_access(user, membership, values["store_ids"])
                db.session.commit()
                persist_audit_event(
                    "PLATFORM_USER_CREATED",
                    event_type="security",
                    entity_type="user",
                    entity_id=str(user.id),
                    details={"site": site.code, "username": user.username, "role": values["role"].code},
                )
                flash(f"{user.full_name} kullanıcısı oluşturuldu. İlk girişte şifre değişikliği zorunludur.", "success")
                return redirect(url_for("platform.site_detail", site_id=site.id))
            for error in errors:
                flash(error, "error")
    return render_template("platform/user_form.html", **_form_user_values(site), form_data=request.form)


@bp.route("/sites/<int:site_id>/users/<int:user_id>/edit", methods=["GET", "POST"])
@platform_admin_required
def edit_user(site_id, user_id):
    site = _site_or_404(site_id)
    membership = UserSiteRole.query.filter_by(site_id=site.id, user_id=user_id).first_or_404()
    user = membership.user
    if user.is_platform_superadmin:
        flash("Platform süper admin hesabı bu ekrandan değiştirilemez.", "info")
        return redirect(url_for("platform.site_detail", site_id=site.id))

    if request.method == "POST":
        if not _csrf_is_valid():
            flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        else:
            errors, values = _validate_user_form(site, user=user)
            if values["is_active"] and _user_limit_reached(site, exclude_user_id=user.id):
                errors.append(
                    f"{site.package.name} paketinde en fazla {site.package.max_users} aktif kullanıcı kullanılabilir."
                )
            if not errors:
                user.username = values["username"]
                user.full_name = values["full_name"]
                user.email = values["email"]
                user.is_active = values["is_active"]
                membership.role_id = values["role"].id
                membership.all_stores = values["all_stores"]
                membership.is_active = values["is_active"]
                if values["password"]:
                    user.password_hash = generate_password_hash(values["password"])
                    user.must_change_password = True
                    user.password_changed_at = None
                if values["reset_two_factor"]:
                    reset_two_factor(user)
                _apply_store_access(user, membership, values["store_ids"])
                db.session.commit()
                persist_audit_event(
                    "PLATFORM_USER_UPDATED",
                    event_type="security",
                    entity_type="user",
                    entity_id=str(user.id),
                    details={
                        "site": site.code,
                        "username": user.username,
                        "role": values["role"].code,
                        "two_factor_reset": values["reset_two_factor"],
                    },
                )
                flash(f"{user.username} kullanıcısı güncellendi.", "success")
                return redirect(url_for("platform.site_detail", site_id=site.id))
            for error in errors:
                flash(error, "error")
    return render_template(
        "platform/user_form.html",
        **_form_user_values(site, user=user, membership=membership),
        form_data=request.form,
    )


@bp.route("/sites/<int:site_id>/users/<int:user_id>/toggle", methods=["POST"])
@platform_admin_required
def toggle_user(site_id, user_id):
    site = _site_or_404(site_id)
    membership = UserSiteRole.query.filter_by(site_id=site.id, user_id=user_id).first_or_404()
    user = membership.user
    if not _csrf_is_valid():
        flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        return redirect(url_for("platform.site_detail", site_id=site.id))
    if user.is_platform_superadmin:
        flash("Platform süper admin hesabı bu ekrandan pasife alınamaz.", "error")
        return redirect(url_for("platform.site_detail", site_id=site.id))

    next_active = not (membership.is_active and user.is_active)
    if next_active and _user_limit_reached(site, exclude_user_id=user.id):
        flash(
            f"{site.package.name} paketinde en fazla {site.package.max_users} aktif kullanıcı kullanılabilir.",
            "error",
        )
        return redirect(url_for("platform.site_detail", site_id=site.id))

    user.is_active = next_active
    membership.is_active = next_active
    db.session.commit()
    persist_audit_event(
        "PLATFORM_SITE_USER_ACTIVATED" if next_active else "PLATFORM_SITE_USER_DEACTIVATED",
        event_type="security",
        entity_type="user_site_role",
        entity_id=str(membership.id),
        details={"site": site.code, "username": user.username, "active": next_active},
    )
    flash(
        f"{user.username} kullanıcısının {site.code} site erişimi "
        f"{'etkinleştirildi' if next_active else 'pasife alındı'}.",
        "success",
    )
    return redirect(url_for("platform.site_detail", site_id=site.id))


@bp.route("/sites/<int:site_id>/roles/<int:role_id>/permissions", methods=["POST"])
@platform_admin_required
def update_role_permissions(site_id, role_id):
    site = _site_or_404(site_id)
    role = Role.query.filter_by(id=role_id, site_id=site.id).first_or_404()
    if not _csrf_is_valid():
        flash("Oturum doğrulaması başarısız. Lütfen tekrar deneyin.", "error")
        return redirect(url_for("platform.site_detail", site_id=site.id))
    allowed = {permission.code: permission for permission in _package_permissions(site)}
    requested_codes = set(request.form.getlist("permission_codes"))
    if not requested_codes <= set(allowed):
        flash("Paket dışında veya geçersiz bir yetki seçildi.", "error")
        return redirect(url_for("platform.site_detail", site_id=site.id))

    for code in tuple(requested_codes):
        permission = allowed[code]
        if permission.parent is not None and permission.parent.code in allowed:
            requested_codes.add(permission.parent.code)
    preserved_outside_package = [
        permission
        for permission in role.permissions
        if permission.code not in allowed
    ]
    role.permissions = preserved_outside_package + [
        allowed[code]
        for code in sorted(requested_codes)
    ]
    db.session.commit()
    persist_audit_event(
        "PLATFORM_ROLE_PERMISSIONS_UPDATED",
        event_type="security",
        entity_type="role",
        entity_id=str(role.id),
        details={"site": site.code, "role": role.code, "permission_count": len(requested_codes)},
    )
    flash(f"{role.name} yetkileri güncellendi.", "success")
    return redirect(url_for("platform.site_detail", site_id=site.id))
