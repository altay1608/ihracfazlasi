"""Idempotent first-run setup for managed deployments."""

import os
from decimal import Decimal

from sqlalchemy import text

from app.extensions import db
from app.models import FinanceActivation, Package, Site, Store, SystemSetting


DELIVERY_RESET_VERSION = "customer_delivery_operational_reset_20260916_v2"


def ensure_automatic_pos_schema():
    """Add automatic POS fields to an existing Vercel PostgreSQL database."""
    if db.engine.dialect.name != "postgresql":
        return
    statements = (
        "ALTER TABLE finance_activations ADD COLUMN IF NOT EXISTS pos_commission_rate NUMERIC(7,4) NOT NULL DEFAULT 2.5500",
        "ALTER TABLE finance_activations ADD COLUMN IF NOT EXISTS pos_settlement_days INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE finance_activations ADD COLUMN IF NOT EXISTS pos_bank_account_id INTEGER NULL",
        "ALTER TABLE sales ADD COLUMN IF NOT EXISTS payment_due_date DATE NULL",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS barcode_mode VARCHAR(20) NOT NULL DEFAULT 'unit'",
        "ALTER TABLE inventory_count_scans DROP CONSTRAINT IF EXISTS uq_inventory_count_scans_count_barcode",
        "CREATE INDEX IF NOT EXISTS ix_sales_payment_due_date ON sales (payment_due_date)",
        "ALTER TABLE pos_reconciliations ADD COLUMN IF NOT EXISTS sale_id INTEGER NULL",
        "ALTER TABLE pos_reconciliations ADD COLUMN IF NOT EXISTS expected_settlement_date DATE NULL",
        "ALTER TABLE pos_reconciliations ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'settled'",
        "ALTER TABLE pos_reconciliations ADD COLUMN IF NOT EXISTS settled_at TIMESTAMP NULL",
        "ALTER TABLE pos_reconciliations ADD COLUMN IF NOT EXISTS auto_generated BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE pos_reconciliations ADD COLUMN IF NOT EXISTS commission_vat_rate NUMERIC(5,2) NOT NULL DEFAULT 10.00",
        "ALTER TABLE pos_reconciliations ADD COLUMN IF NOT EXISTS commission_vat_amount NUMERIC(14,2) NOT NULL DEFAULT 0",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_reconciliation_sale ON pos_reconciliations (sale_id)",
        "CREATE INDEX IF NOT EXISTS ix_pos_reconciliations_expected_settlement_date ON pos_reconciliations (expected_settlement_date)",
        "CREATE INDEX IF NOT EXISTS ix_pos_reconciliations_status ON pos_reconciliations (status)",
        "CREATE INDEX IF NOT EXISTS ix_pos_reconciliations_auto_generated ON pos_reconciliations (auto_generated)",
        "UPDATE pos_reconciliations SET settled_at = occurred_at WHERE settled_at IS NULL AND status = 'settled'",
    )
    with db.engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def reset_customer_delivery_data_once(site_id):
    """Clear one customer's operational data once while preserving access and setup."""
    marker_key = f"{DELIVERY_RESET_VERSION}:{int(site_id)}"
    if db.engine.dialect.name == "postgresql":
        db.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 16092026})
    existing_marker = db.session.get(SystemSetting, marker_key)
    if existing_marker is not None:
        db.session.commit()
        return False

    params = {"site_id": int(site_id)}
    delete_statements = (
        "DELETE FROM inventory_count_scans WHERE site_id = :site_id",
        "DELETE FROM inventory_count_lines WHERE site_id = :site_id",
        "DELETE FROM inventory_counts WHERE site_id = :site_id",
        "DELETE FROM return_items WHERE site_id = :site_id",
        "DELETE FROM returns WHERE site_id = :site_id",
        "DELETE FROM product_barcodes WHERE site_id = :site_id",
        "DELETE FROM supplier_invoice_lines WHERE invoice_id IN (SELECT id FROM supplier_invoices WHERE site_id = :site_id)",
        "DELETE FROM supplier_invoices WHERE site_id = :site_id",
        "DELETE FROM personnel_advance_settlements WHERE record_id IN (SELECT id FROM personnel_finance_records WHERE site_id = :site_id)",
        "DELETE FROM finance_approvals WHERE site_id = :site_id",
        "DELETE FROM personnel_finance_records WHERE site_id = :site_id",
        "DELETE FROM expense_vouchers WHERE site_id = :site_id",
        "DELETE FROM daily_cash_closings WHERE site_id = :site_id",
        "DELETE FROM obligation_payments WHERE site_id = :site_id",
        "DELETE FROM short_term_obligations WHERE site_id = :site_id",
        "DELETE FROM obligation_recurrence_plans WHERE site_id = :site_id",
        "DELETE FROM current_settlements WHERE site_id = :site_id",
        "DELETE FROM current_entries WHERE site_id = :site_id",
        "DELETE FROM pos_reconciliations WHERE site_id = :site_id",
        "DELETE FROM finance_source_states WHERE site_id = :site_id",
        "DELETE FROM finance_transfers WHERE site_id = :site_id",
        "DELETE FROM monthly_overhead_budgets WHERE site_id = :site_id",
        "DELETE FROM finance_movements WHERE site_id = :site_id",
        "DELETE FROM current_accounts WHERE site_id = :site_id",
        "DELETE FROM sale_items WHERE site_id = :site_id",
        "DELETE FROM sales WHERE site_id = :site_id",
        "DELETE FROM inventory_transactions WHERE site_id = :site_id",
        "DELETE FROM store_inventories WHERE site_id = :site_id",
        "DELETE FROM products WHERE site_id = :site_id",
        "DELETE FROM audit_logs WHERE site_id = :site_id",
        "DELETE FROM site_document_sequences WHERE site_id = :site_id",
        "DELETE FROM finance_payment_mappings WHERE site_id = :site_id",
        "UPDATE finance_activations SET pos_bank_account_id = NULL WHERE site_id = :site_id",
        "DELETE FROM finance_accounts WHERE site_id = :site_id AND is_system = FALSE",
        "DELETE FROM finance_categories WHERE site_id = :site_id AND is_system = FALSE",
    )
    try:
        for statement in delete_statements:
            db.session.execute(text(statement), params)

        from app.services.finance import ensure_default_finance_setup

        stores = Store.query.filter_by(site_id=site_id).order_by(Store.id.asc()).all()
        for store in stores:
            accounts, _categories = ensure_default_finance_setup(site_id, store.id)
            activation = FinanceActivation.query.filter_by(
                site_id=site_id,
                store_id=store.id,
            ).one_or_none()
            if activation is not None:
                activation.pos_commission_rate = Decimal("2.5500")
                activation.pos_settlement_days = 1
                activation.pos_bank_account_id = accounts["BANK"].id

        db.session.add(SystemSetting(key=marker_key, value="completed"))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return True


def ensure_deployment_store():
    """Create the customer site/store required by tenant-scoped records."""
    package = Package.query.filter_by(code="PRO").first()
    if package is None:
        package = Package(
            code="PRO",
            name="Pro",
            description="Tüm mağaza yönetimi özellikleri",
            max_stores=5,
            max_users=20,
            is_active=True,
        )
        db.session.add(package)
        db.session.flush()

    site_code = (os.getenv("CUSTOMER_SITE_CODE") or "IFG").strip().upper()
    site_name = (os.getenv("STORE_NAME") or "İhraç Fazlası Giyim").strip()
    site = Site.query.filter_by(code=site_code).first()
    if site is None:
        site = Site(
            package=package,
            code=site_code,
            name=site_name,
            is_sandbox=False,
            is_active=True,
        )
        db.session.add(site)
        db.session.flush()

    store_code = (os.getenv("CUSTOMER_STORE_CODE") or "MERKEZ").strip().upper()
    store = Store.query.filter_by(site_id=site.id, code=store_code).first()
    if store is None:
        store = Store(
            site=site,
            code=store_code,
            name=(os.getenv("STORE_LOCATION_NAME") or "Merkez Mağaza").strip(),
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

    db.session.commit()
    return site, store
