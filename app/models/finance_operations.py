"""Staff-friendly operational accounting records layered on the immutable ledger."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.extensions import db
from app.services.identity_access import get_active_site_id, get_active_store_id


class DailyCashClosing(db.Model):
    __tablename__ = "daily_cash_closings"
    __table_args__ = (
        UniqueConstraint("site_id", "store_id", "business_date", name="uq_daily_closing_scope_date"),
        CheckConstraint("status IN ('closed','reopened')", name="ck_daily_closing_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=get_active_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=get_active_store_id, index=True)
    business_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    expected_cash = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    counted_cash = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    cash_difference = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    expected_card = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    counted_card = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    card_difference = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    expected_transfer = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    counted_transfer = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    transfer_difference = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    handover_from = db.Column(db.String(140), nullable=False)
    handover_to = db.Column(db.String(140), nullable=True)
    note = db.Column(db.String(500), nullable=True)
    closed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    closed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default="closed", index=True)
    reopened_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reopened_at = db.Column(db.DateTime, nullable=True)
    reopen_reason = db.Column(db.String(500), nullable=True)


class ExpenseVoucher(db.Model):
    __tablename__ = "expense_vouchers"
    __table_args__ = (
        CheckConstraint("gross_amount > 0", name="ck_expense_voucher_positive"),
        CheckConstraint("status IN ('pending','approved','rejected')", name="ck_expense_voucher_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=get_active_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=get_active_store_id, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("finance_categories.id"), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    vendor = db.Column(db.String(180), nullable=True)
    document_no = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(500), nullable=False)
    net_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    vat_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    gross_amount = db.Column(db.Numeric(14, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    movement_id = db.Column(db.Integer, db.ForeignKey("finance_movements.id"), nullable=True, unique=True)
    attachment_name = db.Column(db.String(255), nullable=True)
    attachment_mime = db.Column(db.String(120), nullable=True)
    attachment_data = db.Column(db.LargeBinary, nullable=True)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    decided_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    decision_note = db.Column(db.String(500), nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    account = db.relationship("FinanceAccount")
    category = db.relationship("FinanceCategory")


class SupplierInvoice(db.Model):
    __tablename__ = "supplier_invoices"
    __table_args__ = (
        UniqueConstraint("site_id", "invoice_no", name="uq_supplier_invoice_site_no"),
        CheckConstraint("gross_amount > 0", name="ck_supplier_invoice_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=get_active_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=get_active_store_id, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("current_accounts.id"), nullable=False, index=True)
    invoice_no = db.Column(db.String(100), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=True, index=True)
    net_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    vat_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    gross_amount = db.Column(db.Numeric(14, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    current_entry_id = db.Column(db.Integer, db.ForeignKey("current_entries.id"), nullable=False, unique=True)
    note = db.Column(db.String(500), nullable=True)
    attachment_name = db.Column(db.String(255), nullable=True)
    attachment_mime = db.Column(db.String(120), nullable=True)
    attachment_data = db.Column(db.LargeBinary, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    supplier = db.relationship("CurrentAccount")
    current_entry = db.relationship("CurrentEntry")
    lines = db.relationship("SupplierInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class SupplierInvoiceLine(db.Model):
    __tablename__ = "supplier_invoice_lines"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_supplier_invoice_line_quantity"),)

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    description = db.Column(db.String(180), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_cost = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    invoice = db.relationship("SupplierInvoice", back_populates="lines")
    product = db.relationship("Product")


class PersonnelFinanceRecord(db.Model):
    __tablename__ = "personnel_finance_records"
    __table_args__ = (
        CheckConstraint("record_type IN ('advance','store_expense')", name="ck_personnel_finance_type"),
        CheckConstraint("amount > 0", name="ck_personnel_finance_positive"),
        CheckConstraint("status IN ('pending','approved','rejected')", name="ck_personnel_finance_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=get_active_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=get_active_store_id, index=True)
    personnel_name = db.Column(db.String(160), nullable=False, index=True)
    record_type = db.Column(db.String(30), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    remaining_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    occurred_on = db.Column(db.Date, nullable=False, default=date.today)
    description = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    movement_id = db.Column(db.Integer, db.ForeignKey("finance_movements.id"), nullable=True, unique=True)
    attachment_name = db.Column(db.String(255), nullable=True)
    attachment_mime = db.Column(db.String(120), nullable=True)
    attachment_data = db.Column(db.LargeBinary, nullable=True)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    decided_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    decision_note = db.Column(db.String(500), nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    account = db.relationship("FinanceAccount")
    settlements = db.relationship("PersonnelAdvanceSettlement", back_populates="record", cascade="all, delete-orphan")


class PersonnelAdvanceSettlement(db.Model):
    __tablename__ = "personnel_advance_settlements"
    __table_args__ = (
        CheckConstraint("settlement_type IN ('cash_return','expense_offset')", name="ck_personnel_settlement_type"),
        CheckConstraint("amount > 0", name="ck_personnel_settlement_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey("personnel_finance_records.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    settlement_type = db.Column(db.String(30), nullable=False)
    finance_account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False)
    cash_movement_id = db.Column(db.Integer, db.ForeignKey("finance_movements.id"), nullable=True, unique=True)
    expense_movement_id = db.Column(db.Integer, db.ForeignKey("finance_movements.id"), nullable=True, unique=True)
    description = db.Column(db.String(500), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    record = db.relationship("PersonnelFinanceRecord", back_populates="settlements")
    account = db.relationship("FinanceAccount")


class FinanceApproval(db.Model):
    __tablename__ = "finance_approvals"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_finance_approval_entity"),
        CheckConstraint("status IN ('pending','approved','rejected')", name="ck_finance_approval_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=get_active_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=get_active_store_id, index=True)
    entity_type = db.Column(db.String(40), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(220), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    decided_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    decision_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)
