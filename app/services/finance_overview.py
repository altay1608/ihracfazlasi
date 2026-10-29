"""Read-only money summary: balances are not revenue or profit.

Period amounts follow ledger posting dates (Istanbul), including corrections
posted during the period. Balances cover all recorded history, regardless of
the selected period. No opening balances, migrations or repairs are written.
"""
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func
from sqlalchemy.orm import aliased

from app.extensions import db
from app.models.finance import FinanceAccount, FinanceMovement
from app.utils import istanbul_day_start_utc


ZERO = Decimal("0.00")


def _money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def build_money_overview(site_id, store_id, start_date, end_date):
    """Return current balances and a non-overlapping period payment breakdown.

    ``net_turnover`` includes credit sales and returns; it is not cash received.
    ``manual_outflows`` includes owner withdrawals and must not be called profit
    expenses. ``overhead_expenses`` is a separate tagged subset, NOT an additional
    payment. ``payments_total`` excludes returns (already deducted in turnover),
    internal transfers and POS settlement transfers. Negative period amounts can
    legitimately occur when an earlier period's payment is reversed.
    """
    if end_date < start_date:
        raise ValueError("Bitiş tarihi başlangıç tarihinden önce olamaz.")

    incoming = case(
        (FinanceMovement.direction == "in", FinanceMovement.amount),
        else_=-FinanceMovement.amount,
    )
    account_rows = db.session.query(
        FinanceAccount, func.coalesce(func.sum(incoming), 0),
    ).outerjoin(FinanceMovement, and_(
        FinanceMovement.account_id == FinanceAccount.id,
        FinanceMovement.site_id == site_id,
        FinanceMovement.store_id == store_id,
    )).filter(
        FinanceAccount.site_id == site_id,
        FinanceAccount.store_id == store_id,
    ).group_by(FinanceAccount.id).order_by(FinanceAccount.display_code, FinanceAccount.id).all()

    result = {key: ZERO for key in (
        "available_money", "cash_balance", "bank_balance", "pos_receivable",
        "credit_receivable", "business_card_balance", "business_card_debt",
        "other_balance", "total_balance",
    )}
    result["accounts"] = []
    for account, amount in account_rows:
        balance = _money(amount)
        # Keep inactive accounts with a remaining balance visible as well.
        if not account.is_active and balance == 0:
            continue
        result["accounts"].append({"account": account, "balance": balance})
        code = account.code.upper()
        if code == "CREDIT":
            key = "credit_receivable"
        elif code == "BIZ_CARD":
            key = "business_card_balance"
        elif account.account_type == "cash":
            key = "cash_balance"
        elif account.account_type == "bank":
            key = "bank_balance"
        elif account.account_type == "pos_receivable":
            key = "pos_receivable"
        else:
            key = "other_balance"
        result[key] += balance
        result["total_balance"] += balance
    result["available_money"] = result["cash_balance"] + result["bank_balance"]
    result["business_card_debt"] = max(-result["business_card_balance"], ZERO)

    original = aliased(FinanceMovement)
    kind = func.coalesce(original.movement_type, FinanceMovement.movement_type)
    direction = func.coalesce(original.direction, FinanceMovement.direction)
    overhead = func.coalesce(original.is_overhead, FinanceMovement.is_overhead)
    expense_sign = -incoming
    selections = {
        "net_turnover": (kind.in_(("sale", "exchange_sale", "return")), incoming),
        "supplier_payments": (and_(kind == "current_settlement", direction == "out"), expense_sign),
        "manual_outflows": (and_(kind == "manual", direction == "out"), expense_sign),
        "obligation_payments": (and_(kind == "obligation_payment", direction == "out"), expense_sign),
        "overhead_expenses": (and_(overhead.is_(True), kind.notin_(("transfer", "pos_reconciliation", "current_settlement", "pos_commission"))), expense_sign),
        "pos_commissions": (kind == "pos_commission", expense_sign),
        "transfer_net": (kind.in_(("transfer", "pos_reconciliation")), incoming),
    }
    values = db.session.query(*[
        func.coalesce(func.sum(case((condition, signed), else_=0)), 0)
        for condition, signed in selections.values()
    ]).outerjoin(original, and_(
        original.id == FinanceMovement.reversal_of_id,
        original.site_id == site_id,
        original.store_id == store_id,
    )).filter(
        FinanceMovement.site_id == site_id,
        FinanceMovement.store_id == store_id,
        FinanceMovement.occurred_at >= istanbul_day_start_utc(start_date),
        FinanceMovement.occurred_at < istanbul_day_start_utc(end_date + timedelta(days=1)),
    ).one()
    period = {key: _money(value) for key, value in zip(selections, values)}
    period["payments_total"] = sum((period[key] for key in (
        "supplier_payments", "manual_outflows", "obligation_payments", "pos_commissions",
    )), ZERO)
    result["period"] = period
    return result
