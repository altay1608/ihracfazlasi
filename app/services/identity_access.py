"""Identity scope rules shared by authentication and user-management flows."""

from flask import has_request_context, session


class IdentityScopeError(ValueError):
    """Raised when an identity is assigned outside its operational boundary."""


def get_active_site_id(default=1):
    if not has_request_context():
        return default
    try:
        return int(session.get("active_site_id") or default)
    except (TypeError, ValueError):
        return default


def get_active_store_id(default=1):
    if not has_request_context():
        return default
    try:
        return int(session.get("active_store_id") or default)
    except (TypeError, ValueError):
        return default


def is_operational_site_allowed(user, site):
    if user is None or site is None:
        return False
    if not getattr(user, "is_active", False) or not getattr(site, "is_active", False):
        return False
    if getattr(user, "is_platform_superadmin", False):
        return bool(getattr(site, "is_sandbox", False))
    return True


def validate_membership_scope(user, site):
    if not is_operational_site_allowed(user, site):
        if getattr(user, "is_platform_superadmin", False):
            raise IdentityScopeError(
                "Platform super admin musteri sitelerinde operasyonel uyelik alamaz."
            )
        raise IdentityScopeError("Kullanici bu site icin operasyonel uyelik alamaz.")


def eligible_operational_memberships(user):
    if user is None or not getattr(user, "is_active", False):
        return ()

    eligible = []
    for membership in getattr(user, "memberships", ()):
        site = getattr(membership, "site", None)
        role = getattr(membership, "role", None)
        if not getattr(membership, "is_active", False):
            continue
        if role is None or not getattr(role, "is_active", False):
            continue
        if is_operational_site_allowed(user, site):
            eligible.append(membership)
    return tuple(eligible)
