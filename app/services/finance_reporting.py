"""Read models for finance screens and the owner dashboard."""

from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from app.models import Store
from app.models.finance import FinanceAccount, FinanceMovement, MonthlyOverheadBudget
from app.utils import istanbul_day_start_utc, quantize_amount, utc_to_istanbul


TURKISH_MONTH_NAMES = (
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık",
)


def month_choice_options(selected=None, months_back=11, months_forward=1):
    """Return localized month choices without relying on process locale."""
    selected_start, _ = month_bounds(selected)
    choices = []
    for offset in range(-int(months_back), int(months_forward) + 1):
        month_index = (selected_start.year * 12 + selected_start.month - 1) + offset
        year, zero_based_month = divmod(month_index, 12)
        value = date(year, zero_based_month + 1, 1)
        choices.append(
            {
                "value": value.strftime("%Y-%m"),
                "label": f"{TURKISH_MONTH_NAMES[value.month - 1]} {value.year}",
            }
        )
    return choices


def month_bounds(value=None):
    selected = value or date.today()
    if isinstance(selected, datetime):
        selected = selected.date()
    start = selected.replace(day=1)
    end = start.replace(day=monthrange(start.year, start.month)[1])
    return start, end


def authorized_store_ids(*, user, site_id, role_id):
    """Return active stores covered by the user's active site membership."""
    if user is None:
        return []
    membership = next(
        (
            membership
            for membership in user.memberships
            if membership.is_active
            and membership.site_id == site_id
            and membership.role_id == role_id
        ),
        None,
    )
    if membership is None:
        return []
    if membership.all_stores:
        return [store.id for store in Store.query.filter_by(site_id=site_id, is_active=True).all()]
    allowed_ids = {access.store_id for access in user.store_access}
    if not allowed_ids:
        return []
    return [
        store.id
        for store in Store.query.filter(
            Store.site_id == site_id,
            Store.id.in_(allowed_ids),
            Store.is_active.is_(True),
        ).all()
    ]


def build_finance_snapshot(*, site_id, store_ids, selected_month=None):
    """Build account balances, operating totals and a cumulative month chart."""
    store_ids = tuple(sorted({int(store_id) for store_id in store_ids}))
    month_start, month_end = month_bounds(selected_month)
    day_count = monthrange(month_start.year, month_start.month)[1]
    empty_chart = [
        {"date": month_start + timedelta(days=index), "gross": Decimal("0.00"), "net": Decimal("0.00")}
        for index in range(day_count)
    ]
    if not store_ids:
        return _snapshot_result(
            [], empty_chart, Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), month_start, month_end
        )

    accounts = (
        FinanceAccount.query.filter(
            FinanceAccount.site_id == site_id,
            FinanceAccount.store_id.in_(store_ids),
            FinanceAccount.is_active.is_(True),
        )
        .execution_options(skip_tenant_scope=True)
        .order_by(FinanceAccount.store_id.asc(), FinanceAccount.name.asc())
        .all()
    )
    all_movements = FinanceMovement.query.filter(
        FinanceMovement.site_id == site_id,
        FinanceMovement.store_id.in_(store_ids),
    ).execution_options(skip_tenant_scope=True).all()
    balances = {account.id: Decimal("0.00") for account in accounts}
    for movement in all_movements:
        if movement.account_id in balances:
            balances[movement.account_id] += _signed_amount(movement)

    account_rows = [
        {
            "account": account,
            "balance": quantize_amount(balances.get(account.id, Decimal("0.00"))),
        }
        for account in accounts
    ]

    start_at = istanbul_day_start_utc(month_start)
    end_at = istanbul_day_start_utc(month_end + timedelta(days=1))
    month_movements = [
        movement
        for movement in all_movements
        if start_at <= movement.occurred_at < end_at
    ]
    movement_by_id = {movement.id: movement for movement in all_movements}
    daily = {
        row["date"]: {"gross": Decimal("0.00"), "net": Decimal("0.00")}
        for row in empty_chart
    }
    for movement in month_movements:
        gross_effect, net_effect = _operating_effect(movement, movement_by_id)
        movement_day = utc_to_istanbul(movement.occurred_at).date()
        daily[movement_day]["gross"] += gross_effect
        daily[movement_day]["net"] += net_effect

    cumulative_gross = Decimal("0.00")
    cumulative_net = Decimal("0.00")
    chart = []
    for current_day in sorted(daily):
        cumulative_gross += daily[current_day]["gross"]
        cumulative_net += daily[current_day]["net"]
        chart.append(
            {
                "date": current_day,
                "gross": quantize_amount(cumulative_gross),
                "net": quantize_amount(cumulative_net),
            }
        )

    overhead = sum(
        (
            budget.amount
            for budget in MonthlyOverheadBudget.query.filter(
                MonthlyOverheadBudget.site_id == site_id,
                MonthlyOverheadBudget.store_id.in_(store_ids),
                MonthlyOverheadBudget.budget_month == month_start,
            ).execution_options(skip_tenant_scope=True).all()
        ),
        Decimal("0.00"),
    )
    actual_overhead = sum(
        (_signed_amount(movement) * Decimal("-1") for movement in month_movements if movement.is_overhead),
        Decimal("0.00"),
    )
    pos_commission_expense = sum(
        (
            _signed_amount(movement) * Decimal("-1")
            for movement in month_movements
            if _effective_movement_type(movement, movement_by_id) == "pos_commission"
        ),
        Decimal("0.00"),
    )
    return _snapshot_result(
        account_rows,
        chart,
        overhead,
        actual_overhead,
        pos_commission_expense,
        month_start,
        month_end,
    )


def _snapshot_result(
    account_rows,
    chart,
    overhead,
    actual_overhead,
    pos_commission_expense,
    month_start,
    month_end,
):
    gross = chart[-1]["gross"] if chart else Decimal("0.00")
    net = chart[-1]["net"] if chart else Decimal("0.00")
    overhead = quantize_amount(overhead)
    actual_overhead = quantize_amount(actual_overhead)
    pos_commission_expense = quantize_amount(pos_commission_expense)
    actual_operating_expense = quantize_amount(actual_overhead + pos_commission_expense)
    planned_daily_overhead = quantize_amount(overhead / Decimal("30"))
    actual_daily_overhead = quantize_amount(actual_overhead / Decimal("30"))
    planned_operating_result = quantize_amount(net - overhead)
    actual_operating_result = quantize_amount(net - actual_operating_expense)
    planned_overhead_ratio = (
        quantize_amount((overhead / net) * Decimal("100")) if net > 0 else Decimal("0.00")
    )
    actual_expense_ratio = (
        quantize_amount((actual_operating_expense / net) * Decimal("100"))
        if net > 0
        else Decimal("0.00")
    )
    planned_operating_margin = (
        quantize_amount((planned_operating_result / net) * Decimal("100"))
        if net > 0
        else Decimal("0.00")
    )
    actual_operating_margin = (
        quantize_amount((actual_operating_result / net) * Decimal("100"))
        if net > 0
        else Decimal("0.00")
    )
    consolidated = quantize_amount(
        sum((row["balance"] for row in account_rows), Decimal("0.00"))
    )
    return {
        "accounts": account_rows,
        "consolidated_balance": consolidated,
        "month_start": month_start,
        "month_end": month_end,
        "chart": chart,
        "gross_revenue": gross,
        "net_revenue": net,
        "overhead": overhead,
        "actual_overhead": actual_overhead,
        "pos_commission_expense": pos_commission_expense,
        "actual_operating_expense": actual_operating_expense,
        "overhead_variance": quantize_amount(overhead - actual_overhead),
        "planned_daily_overhead": planned_daily_overhead,
        "actual_daily_overhead": actual_daily_overhead,
        "daily_overhead": planned_daily_overhead,
        "planned_operating_result": planned_operating_result,
        "actual_operating_result": actual_operating_result,
        "planned_overhead_ratio": planned_overhead_ratio,
        "actual_expense_ratio": actual_expense_ratio,
        "planned_operating_margin": planned_operating_margin,
        "actual_operating_margin": actual_operating_margin,
        # Backward-compatible aliases for any external report integrations.
        "estimated_result": planned_operating_result,
        "overhead_ratio": planned_overhead_ratio,
        "estimated_margin": planned_operating_margin,
    }


def _signed_amount(movement):
    return movement.amount if movement.direction == "in" else -movement.amount


def _operating_effect(movement, movement_by_id):
    movement_type = _effective_movement_type(movement, movement_by_id)
    direction = movement.direction

    signed = movement.amount if direction == "in" else -movement.amount
    if movement_type in {"sale", "exchange_sale"}:
        return signed, signed
    if movement_type == "return":
        return Decimal("0.00"), signed
    return Decimal("0.00"), Decimal("0.00")


def _effective_movement_type(movement, movement_by_id):
    if movement.movement_type == "reversal" and movement.reversal_of_id is not None:
        original = movement_by_id.get(movement.reversal_of_id)
        if original is not None:
            return original.movement_type
    return movement.movement_type
