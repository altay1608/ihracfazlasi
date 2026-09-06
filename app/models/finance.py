"""Store-scoped finance ledger, current accounts, and planning models."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, UniqueConstraint, event, inspect

from app.extensions import db
from app.services.identity_access import get_active_site_id, get_active_store_id


def _site_id():
    return get_active_site_id()


def _store_id():
    return get_active_store_id()


class FinanceActivation(db.Model):
    __tablename__ = "finance_activations"
    __table_args__ = (UniqueConstraint("site_id", "store_id", name="uq_finance_activation_scope"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    activated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    activated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FinanceAccount(db.Model):
    __tablename__ = "finance_accounts"
    __table_args__ = (
        UniqueConstraint("site_id", "store_id", "code", name="uq_finance_account_scope_code"),
        UniqueConstraint(
            "site_id",
            "store_id",
            "display_code",
            name="uq_finance_account_scope_display_code",
        ),
        CheckConstraint("account_type IN ('cash','bank','pos_receivable')", name="ck_finance_account_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    code = db.Column(db.String(40), nullable=False)
    display_code = db.Column(db.String(40), nullable=False, default="-")
    name = db.Column(db.String(140), nullable=False)
    account_type = db.Column(db.String(30), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="TRY")
    is_system = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FinancePaymentMapping(db.Model):
    __tablename__ = "finance_payment_mappings"
    __table_args__ = (
        UniqueConstraint("site_id", "store_id", "payment_method", name="uq_finance_payment_mapping"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    payment_method = db.Column(db.String(80), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    account = db.relationship("FinanceAccount")


@event.listens_for(FinanceAccount, "before_update")
def _prevent_finance_account_display_code_change(_mapper, _connection, target):
    if inspect(target).attrs.display_code.history.has_changes():
        raise ValueError("Finans hesap kodu oluşturulduktan sonra değiştirilemez.")


class FinanceCategory(db.Model):
    __tablename__ = "finance_categories"
    __table_args__ = (
        UniqueConstraint("site_id", "code", name="uq_finance_category_site_code"),
        CheckConstraint("direction IN ('in','out','both')", name="ck_finance_category_direction"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(140), nullable=False)
    direction = db.Column(db.String(10), nullable=False)
    default_is_overhead = db.Column(db.Boolean, nullable=False, default=False)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FinanceMovement(db.Model):
    __tablename__ = "finance_movements"
    __table_args__ = (
        UniqueConstraint("site_id", "store_id", "source_key", name="uq_finance_movement_source_key"),
        CheckConstraint("direction IN ('in','out')", name="ck_finance_movement_direction"),
        CheckConstraint("amount > 0", name="ck_finance_movement_positive_amount"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("finance_categories.id"), nullable=False, index=True)
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    direction = db.Column(db.String(3), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    movement_type = db.Column(db.String(40), nullable=False, index=True)
    is_overhead = db.Column(db.Boolean, nullable=False, default=False, index=True)
    description = db.Column(db.String(500), nullable=True)
    document_no = db.Column(db.String(100), nullable=True)
    source_type = db.Column(db.String(50), nullable=False, index=True)
    source_id = db.Column(db.Integer, nullable=True, index=True)
    source_key = db.Column(db.String(180), nullable=False)
    reversal_of_id = db.Column(db.Integer, db.ForeignKey("finance_movements.id"), nullable=True, index=True)
    pair_key = db.Column(db.String(80), nullable=True, index=True)
    current_account_id = db.Column(db.Integer, db.ForeignKey("current_accounts.id"), nullable=True, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    account = db.relationship("FinanceAccount")
    category = db.relationship("FinanceCategory")
    reversal_of = db.relationship("FinanceMovement", remote_side=[id])

    @property
    def display_category_name(self):
        if self.movement_type == "pos_reconciliation":
            return "POS Mutabakatı"
        return self.category.name if self.category is not None else "-"


@event.listens_for(FinanceMovement, "before_update")
@event.listens_for(FinanceMovement, "before_delete")
def _prevent_finance_movement_mutation(_mapper, _connection, _target):
    raise ValueError("Finans hareketleri degistirilemez; ters kayit olusturun.")


class FinanceSourceState(db.Model):
    __tablename__ = "finance_source_states"
    __table_args__ = (
        UniqueConstraint("site_id", "store_id", "source_type", "source_id", name="uq_finance_source_state"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    source_type = db.Column(db.String(50), nullable=False)
    source_id = db.Column(db.Integer, nullable=False)
    fingerprint = db.Column(db.String(64), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    last_movement_id = db.Column(db.Integer, db.ForeignKey("finance_movements.id"), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class FinanceTransfer(db.Model):
    __tablename__ = "finance_transfers"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_finance_transfer_positive_amount"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    from_account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(500), nullable=True)
    pair_key = db.Column(db.String(80), nullable=False, unique=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class PosReconciliation(db.Model):
    __tablename__ = "pos_reconciliations"
    __table_args__ = (
        CheckConstraint("gross_amount > 0", name="ck_pos_reconciliation_gross_positive"),
        CheckConstraint(
            "commission_rate >= 0 AND commission_rate < 100",
            name="ck_pos_reconciliation_rate_range",
        ),
        CheckConstraint("commission_amount >= 0", name="ck_pos_reconciliation_commission_nonnegative"),
        CheckConstraint("net_amount > 0", name="ck_pos_reconciliation_net_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    pos_account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False)
    bank_account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False)
    gross_amount = db.Column(db.Numeric(14, 2), nullable=False)
    commission_rate = db.Column(db.Numeric(7, 4), nullable=False, default=Decimal("0.0000"))
    commission_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    net_amount = db.Column(db.Numeric(14, 2), nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reference = db.Column(db.String(120), nullable=True)
    pair_key = db.Column(db.String(80), nullable=False, unique=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CurrentAccount(db.Model):
    __tablename__ = "current_accounts"
    __table_args__ = (
        UniqueConstraint("site_id", "code", name="uq_current_account_site_code"),
        CheckConstraint(
            "account_category IN ('customer','supplier')",
            name="ck_current_account_category",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    code = db.Column(db.String(40), nullable=False)
    account_category = db.Column(db.String(20), nullable=False, default="customer", index=True)
    name = db.Column(db.String(180), nullable=False)
    tax_no = db.Column(db.String(30), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(180), nullable=True)
    note = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CurrentEntry(db.Model):
    __tablename__ = "current_entries"
    __table_args__ = (
        CheckConstraint("entry_type IN ('receivable','payable')", name="ck_current_entry_type"),
        CheckConstraint("amount > 0", name="ck_current_entry_amount_positive"),
        CheckConstraint("remaining_amount >= 0", name="ck_current_entry_remaining_nonnegative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    current_account_id = db.Column(db.Integer, db.ForeignKey("current_accounts.id"), nullable=False, index=True)
    entry_type = db.Column(db.String(12), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    remaining_amount = db.Column(db.Numeric(14, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="open")
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CurrentSettlement(db.Model):
    __tablename__ = "current_settlements"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_current_settlement_positive"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    current_entry_id = db.Column(db.Integer, db.ForeignKey("current_entries.id"), nullable=False, index=True)
    finance_account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    movement_id = db.Column(db.Integer, db.ForeignKey("finance_movements.id"), nullable=False, unique=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class MonthlyOverheadBudget(db.Model):
    __tablename__ = "monthly_overhead_budgets"
    __table_args__ = (
        UniqueConstraint("site_id", "store_id", "budget_month", "category_id", name="uq_monthly_overhead_scope"),
        CheckConstraint("amount >= 0", name="ck_monthly_overhead_nonnegative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    budget_month = db.Column(db.Date, nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("finance_categories.id"), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    note = db.Column(db.String(500), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ObligationRecurrencePlan(db.Model):
    __tablename__ = "obligation_recurrence_plans"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_obligation_recurrence_plan_positive"),
        CheckConstraint(
            "recurrence IN ('weekly','monthly')",
            name="ck_obligation_recurrence_plan_type",
        ),
        CheckConstraint(
            "status IN ('active','stopped','completed')",
            name="ck_obligation_recurrence_plan_status",
        ),
        CheckConstraint(
            "anchor_day >= 1 AND anchor_day <= 31",
            name="ck_obligation_recurrence_plan_anchor_day",
        ),
        CheckConstraint(
            "next_sequence >= 2",
            name="ck_obligation_recurrence_plan_next_sequence",
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= first_due_date",
            name="ck_obligation_recurrence_plan_end_date",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    current_account_id = db.Column(db.Integer, db.ForeignKey("current_accounts.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("finance_categories.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    recurrence = db.Column(db.String(20), nullable=False)
    first_due_date = db.Column(db.Date, nullable=False)
    next_due_date = db.Column(db.Date, nullable=False, index=True)
    anchor_day = db.Column(db.Integer, nullable=False)
    next_sequence = db.Column(db.Integer, nullable=False, default=2)
    end_date = db.Column(db.Date, nullable=True)
    is_overhead = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    note = db.Column(db.String(500), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    stopped_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShortTermObligation(db.Model):
    __tablename__ = "short_term_obligations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_short_obligation_positive"),
        CheckConstraint("remaining_amount >= 0", name="ck_short_obligation_remaining"),
        CheckConstraint(
            "recurrence_plan_id IS NULL OR due_date IS NOT NULL",
            name="ck_short_obligation_plan_due_date",
        ),
        CheckConstraint(
            "(recurrence_plan_id IS NULL AND recurrence_sequence IS NULL) OR "
            "(recurrence_plan_id IS NOT NULL AND recurrence_sequence > 0)",
            name="ck_short_obligation_plan_sequence",
        ),
        UniqueConstraint(
            "recurrence_plan_id",
            "due_date",
            name="uq_short_obligation_plan_due_date",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    current_account_id = db.Column(db.Integer, db.ForeignKey("current_accounts.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("finance_categories.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    remaining_amount = db.Column(db.Numeric(14, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    recurrence = db.Column(db.String(20), nullable=False, default="once")
    recurrence_plan_id = db.Column(
        db.Integer,
        db.ForeignKey("obligation_recurrence_plans.id"),
        nullable=True,
        index=True,
    )
    recurrence_sequence = db.Column(db.Integer, nullable=True)
    is_overhead = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default="open")
    note = db.Column(db.String(500), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ObligationPayment(db.Model):
    __tablename__ = "obligation_payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_obligation_payment_positive"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, default=_site_id, index=True)
    store_id = db.Column(db.Integer, db.ForeignKey("stores.id"), nullable=False, default=_store_id, index=True)
    obligation_id = db.Column(db.Integer, db.ForeignKey("short_term_obligations.id"), nullable=False, index=True)
    finance_account_id = db.Column(db.Integer, db.ForeignKey("finance_accounts.id"), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    movement_id = db.Column(db.Integer, db.ForeignKey("finance_movements.id"), nullable=False, unique=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
