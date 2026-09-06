"""Request-bound tenant isolation for all operational ORM statements."""

from contextlib import contextmanager

from flask import has_request_context, session
from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.services.identity_access import get_active_site_id, get_active_store_id


_LISTENERS_REGISTERED = False


def _scoped_models():
    from app.models import (
        Category,
        InventoryCount,
        InventoryCountLine,
        InventoryCountScan,
        InventoryTransaction,
        PaymentMethod,
        Product,
        ProductBarcode,
        RetailMultiplier,
        Return,
        ReturnItem,
        ReturnReason,
        Sale,
        SaleItem,
        StoreInventory,
        Variant,
    )

    site_models = (
        Category,
        Variant,
        PaymentMethod,
        ReturnReason,
        RetailMultiplier,
        Product,
    )
    store_models = (
        ProductBarcode,
        StoreInventory,
        Sale,
        SaleItem,
        Return,
        ReturnItem,
        InventoryCount,
        InventoryCountLine,
        InventoryCountScan,
        InventoryTransaction,
    )
    return site_models, store_models


def _tenant_scope_is_active():
    return has_request_context() and bool(session.get("auth_user"))


def _apply_tenant_criteria(execute_state):
    if not _tenant_scope_is_active():
        return
    if execute_state.execution_options.get("skip_tenant_scope"):
        return
    if not (execute_state.is_select or execute_state.is_update or execute_state.is_delete):
        return

    active_site_id = get_active_site_id()
    active_store_id = get_active_store_id()
    site_models, store_models = _scoped_models()
    statement = execute_state.statement

    for model in site_models:
        statement = statement.options(
            with_loader_criteria(
                model,
                lambda entity: entity.site_id == active_site_id,
                include_aliases=True,
            )
        )
    for model in store_models:
        statement = statement.options(
            with_loader_criteria(
                model,
                lambda entity: (
                    (entity.site_id == active_site_id) & (entity.store_id == active_store_id)
                ),
                include_aliases=True,
            )
        )
    execute_state.statement = statement


def _validate_pending_scope(orm_session, _flush_context, _instances):
    if not _tenant_scope_is_active():
        return
    if orm_session.info.get("platform_site_provisioning"):
        return

    active_site_id = get_active_site_id()
    active_store_id = get_active_store_id()
    site_models, store_models = _scoped_models()
    site_types = tuple(site_models)
    store_types = tuple(store_models)

    for record in orm_session.new.union(orm_session.dirty):
        if isinstance(record, store_types):
            if getattr(record, "site_id", None) is None:
                record.site_id = active_site_id
            if getattr(record, "store_id", None) is None:
                record.store_id = active_store_id
            if record.site_id != active_site_id or record.store_id != active_store_id:
                raise ValueError("Kayit aktif site veya magaza kapsami disina cikamaz.")
        elif isinstance(record, site_types):
            if getattr(record, "site_id", None) is None:
                record.site_id = active_site_id
            if record.site_id != active_site_id:
                raise ValueError("Kayit aktif site kapsami disina cikamaz.")


@contextmanager
def platform_site_provisioning_scope():
    """Allow one platform-admin controlled transaction to seed a new tenant."""
    from app.extensions import db
    from app.services.user_auth import get_current_user

    user = get_current_user()
    if user is None or not user.is_platform_superadmin:
        raise PermissionError("Site kurulumu yalnız platform süper admin tarafından yapılabilir.")

    orm_session = db.session()
    previous = orm_session.info.get("platform_site_provisioning")
    orm_session.info["platform_site_provisioning"] = True
    try:
        yield
    finally:
        if previous is None:
            orm_session.info.pop("platform_site_provisioning", None)
        else:
            orm_session.info["platform_site_provisioning"] = previous


def register_tenant_scope():
    global _LISTENERS_REGISTERED
    if _LISTENERS_REGISTERED:
        return
    event.listen(Session, "do_orm_execute", _apply_tenant_criteria)
    event.listen(Session, "before_flush", _validate_pending_scope)
    _LISTENERS_REGISTERED = True
