"""Owner-only finance management screens."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from hmac import compare_digest

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import case
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import PaymentMethod, Store
from app.models.finance import (
    CurrentAccount,
    CurrentEntry,
    FinanceAccount,
    FinanceActivation,
    FinanceCategory,
    FinanceMovement,
    FinancePaymentMapping,
    FinanceTransfer,
    MonthlyOverheadBudget,
    ObligationRecurrencePlan,
    PosReconciliation,
    ShortTermObligation,
)
from app.services.access_control import permission_required
from app.services.finance import (
    CURRENT_ACCOUNT_CATEGORIES,
    FinanceConfigurationError,
    activate_finance,
    adjust_opening_balance,
    create_account_transfer,
    create_current_account,
    create_current_entry,
    create_finance_account,
    create_finance_category,
    create_manual_movement,
    create_pos_reconciliation,
    create_short_term_obligation,
    get_account_balance,
    pay_short_term_obligation,
    resume_obligation_recurrence_plan,
    reverse_movement,
    set_payment_mapping,
    settle_current_entry,
    stop_obligation_recurrence_plan,
    sync_recurring_obligations,
    upsert_monthly_overhead_budget,
    update_obligation_recurrence_plan,
    update_finance_category_overhead_default,
)
from app.services.finance_reporting import (
    authorized_store_ids,
    build_finance_snapshot,
    month_choice_options,
)
from app.services.identity_access import get_active_site_id, get_active_store_id
from app.services.user_auth import database_authentication_active, get_current_user
from app.utils import (
    is_ajax_request,
    is_modal_request,
    istanbul_day_start_utc,
    istanbul_to_utc,
    now_in_istanbul,
)


bp = Blueprint("finance", __name__, url_prefix="/finance")


@bp.get("/")
@permission_required("finance.ledger.view")
def index():
    site_id, store_id = _active_scope()
    selected_store_ids, show_all_stores, can_show_all = _selected_store_scope(site_id, store_id)
    date_from = _parse_date(request.args.get("date_from")) or date.today().replace(day=1)
    date_to = _parse_date(request.args.get("date_to")) or date.today()
    if date_to < date_from:
        date_from, date_to = date_to, date_from

    pos_ledger_order = case(
        (FinanceMovement.movement_type == "pos_commission", 3),
        (
            (FinanceMovement.movement_type == "pos_reconciliation")
            & (FinanceMovement.direction == "out"),
            2,
        ),
        (
            (FinanceMovement.movement_type == "pos_reconciliation")
            & (FinanceMovement.direction == "in"),
            1,
        ),
        else_=0,
    )
    movements = (
        FinanceMovement.query.options(
            joinedload(FinanceMovement.account),
            joinedload(FinanceMovement.category),
        ).filter(
            FinanceMovement.site_id == site_id,
            FinanceMovement.store_id.in_(selected_store_ids),
            FinanceMovement.occurred_at >= istanbul_day_start_utc(date_from),
            FinanceMovement.occurred_at < istanbul_day_start_utc(date_to + timedelta(days=1)),
        ).execution_options(skip_tenant_scope=True)
        .order_by(
            FinanceMovement.occurred_at.desc(),
            pos_ledger_order.desc(),
            FinanceMovement.id.desc(),
        )
        .limit(500)
        .all()
    )
    selected_month = date_from.replace(day=1)
    snapshot = build_finance_snapshot(
        site_id=site_id,
        store_ids=selected_store_ids,
        selected_month=selected_month,
    )
    stores = {
        store.id: store
        for store in Store.query.filter(Store.id.in_(selected_store_ids)).all()
    }
    return render_template(
        "finance/index.html",
        movements=movements,
        snapshot=snapshot,
        stores=stores,
        date_from=date_from,
        date_to=date_to,
        show_all_stores=show_all_stores,
        can_show_all=can_show_all,
        activation=FinanceActivation.query.filter_by(site_id=site_id, store_id=store_id).one_or_none(),
    )


@bp.route("/accounts", methods=["GET"])
@permission_required("finance.accounts.view")
def accounts():
    site_id, store_id = _active_scope()
    categories = (
        FinanceCategory.query.filter_by(site_id=site_id)
        .order_by(FinanceCategory.is_system.desc(), FinanceCategory.name.asc())
        .all()
    )
    if request.args.get("partial") == "categories":
        return render_template("finance/_categories_section.html", categories=categories)
    account_rows = [
        {"account": account, "balance": get_account_balance(account)}
        for account in FinanceAccount.query.filter_by(site_id=site_id, store_id=store_id)
        .order_by(FinanceAccount.is_system.desc(), FinanceAccount.name.asc())
        .all()
    ]
    mappings = {
        mapping.payment_method: mapping
        for mapping in FinancePaymentMapping.query.filter_by(site_id=site_id, store_id=store_id).all()
    }
    return render_template(
        "finance/accounts.html",
        activation=FinanceActivation.query.filter_by(site_id=site_id, store_id=store_id).one_or_none(),
        account_rows=account_rows,
        accounts=[row["account"] for row in account_rows if row["account"].is_active],
        categories=categories,
        payment_methods=PaymentMethod.query.filter_by(site_id=site_id).order_by(PaymentMethod.name.asc()).all(),
        mappings=mappings,
    )


@bp.post("/activate")
@permission_required("finance.accounts.manage")
def activate():
    _require_csrf()
    site_id, store_id = _active_scope()
    try:
        activate_finance(
            site_id,
            store_id,
            opening_cash=_parse_money(request.form.get("opening_cash")),
            activated_at=datetime.utcnow(),
        )
        db.session.commit()
        flash("Finans Yönetimi bu mağaza için aktive edildi.", "success")
    except (FinanceConfigurationError, InvalidOperation) as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for("finance.accounts"))


@bp.post("/accounts/opening")
@permission_required("finance.accounts.manage")
def adjust_opening():
    _require_csrf()
    site_id, store_id = _active_scope()
    try:
        adjust_opening_balance(
            site_id=site_id,
            store_id=store_id,
            target_amount=_parse_money(request.form.get("opening_cash")),
            reason=request.form.get("reason"),
            allow_after_activity=True,
        )
        db.session.commit()
        flash("Devir bakiyesi değiştirilemez deftere işlendi.", "success")
    except (FinanceConfigurationError, InvalidOperation) as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for("finance.accounts"))


@bp.post("/accounts/create")
@permission_required("finance.accounts.manage")
def create_account():
    _require_csrf()
    site_id, store_id = _active_scope()
    return _commit_action(
        lambda: create_finance_account(
            site_id=site_id,
            store_id=store_id,
            code=request.form.get("code"),
            name=request.form.get("name"),
            account_type=request.form.get("account_type"),
        ),
        "Finans hesabı oluşturuldu.",
        "finance.accounts",
    )


@bp.post("/categories/create")
@permission_required("finance.accounts.manage")
def create_category():
    _require_csrf()
    site_id, _store_id = _active_scope()
    return _commit_action(
        lambda: create_finance_category(
            site_id=site_id,
            code=request.form.get("code"),
            name=request.form.get("name"),
            direction=request.form.get("direction"),
            default_is_overhead=request.form.get("default_is_overhead") == "1",
        ),
        "Finans kategorisi oluşturuldu.",
        "finance.accounts",
    )


@bp.route("/categories/<int:category_id>/overhead-default", methods=["GET", "POST"])
@permission_required("finance.accounts.manage")
def update_category_overhead_default(category_id):
    site_id, _store_id = _active_scope()
    category = FinanceCategory.query.filter_by(id=category_id, site_id=site_id).one_or_none()
    if category is None or category.is_system or category.direction == "in":
        abort(404)

    if request.method == "GET":
        if not is_modal_request():
            return redirect(url_for("finance.accounts"))
        return render_template("finance/_category_overhead_modal.html", category=category)

    _require_csrf()
    try:
        update_finance_category_overhead_default(
            site_id=site_id,
            category_id=category_id,
            default_is_overhead=request.form.get("default_is_overhead") == "1",
        )
        db.session.commit()
    except (FinanceConfigurationError, InvalidOperation, ValueError) as exc:
        db.session.rollback()
        if is_ajax_request():
            return (
                jsonify(
                    {
                        "success": False,
                        "message": str(exc),
                        "html": render_template("finance/_category_overhead_modal.html", category=category),
                    }
                ),
                400,
            )
        flash(str(exc), "error")
        return redirect(url_for("finance.accounts"))

    message = "Kategori genel gider varsayılanı güncellendi; geçmiş kayıtlar değişmedi."
    if is_ajax_request():
        return jsonify(
            {
                "success": True,
                "message": message,
                "refresh_target": "#finance-categories-section",
                "refresh_url": url_for("finance.accounts", partial="categories"),
            }
        )
    flash(message, "success")
    return redirect(url_for("finance.accounts"))


@bp.post("/payment-mappings")
@permission_required("finance.accounts.manage")
def update_payment_mapping():
    _require_csrf()
    site_id, store_id = _active_scope()
    return _commit_action(
        lambda: set_payment_mapping(
            site_id=site_id,
            store_id=store_id,
            payment_method=request.form.get("payment_method"),
            account_id=_parse_int(request.form.get("account_id")),
        ),
        "Ödeme yöntemi eşlemesi güncellendi.",
        "finance.accounts",
    )


@bp.route("/manual", methods=["GET", "POST"])
@permission_required("finance.manual.create")
def manual():
    site_id, store_id = _active_scope()
    if request.method == "POST":
        _require_csrf()
        return _commit_action(
            lambda: create_manual_movement(
                site_id=site_id,
                store_id=store_id,
                account_id=_parse_int(request.form.get("account_id")),
                category_id=_parse_int(request.form.get("category_id")),
                direction=request.form.get("direction"),
                amount=_parse_money(request.form.get("amount")),
                occurred_at=_parse_datetime(request.form.get("occurred_at")),
                description=request.form.get("description"),
                document_no=request.form.get("document_no"),
                current_account_id=_optional_int(request.form.get("current_account_id")),
                is_overhead=_parse_overhead_choice(),
            ),
            "Manuel finans hareketi kaydedildi.",
            "finance.manual",
        )
    manual_movements = (
        FinanceMovement.query.options(
            joinedload(FinanceMovement.account),
            joinedload(FinanceMovement.category),
        )
        .filter_by(site_id=site_id, store_id=store_id, source_type="manual")
        .order_by(FinanceMovement.occurred_at.desc(), FinanceMovement.id.desc())
        .limit(250)
        .all()
    )
    context = _form_context(site_id, store_id)
    context.update(
        manual_movements=manual_movements,
        reversed_movement_ids={
            movement.reversal_of_id
            for movement in manual_movements
            if movement.reversal_of_id is not None
        },
    )
    return render_template("finance/manual.html", **context)


@bp.post("/movements/<int:movement_id>/reverse")
@permission_required("finance.manual.create")
def reverse(movement_id):
    _require_csrf()
    site_id, store_id = _active_scope()
    movement = FinanceMovement.query.filter_by(id=movement_id, site_id=site_id, store_id=store_id).first_or_404()
    if movement.source_type != "manual" or movement.reversal_of_id is not None:
        abort(409)
    return _commit_action(
        lambda: reverse_movement(movement, request.form.get("reason"), datetime.utcnow()),
        "Ters kayıt oluşturuldu; asıl hareket korundu.",
        "finance.manual",
    )


@bp.route("/transfers", methods=["GET", "POST"])
@permission_required("finance.transfer.create")
def transfers():
    site_id, store_id = _active_scope()
    if request.method == "POST":
        _require_csrf()
        return _commit_action(
            lambda: create_account_transfer(
                site_id=site_id,
                store_id=store_id,
                from_account_id=_parse_int(request.form.get("from_account_id")),
                to_account_id=_parse_int(request.form.get("to_account_id")),
                amount=_parse_money(request.form.get("amount")),
                occurred_at=_parse_datetime(request.form.get("occurred_at")),
                description=request.form.get("description"),
            ),
            "Hesap transferi iki bağlı hareket olarak kaydedildi.",
            "finance.transfers",
        )
    context = _form_context(site_id, store_id)
    context["transfers"] = (
        FinanceTransfer.query.filter_by(site_id=site_id, store_id=store_id)
        .order_by(FinanceTransfer.occurred_at.desc(), FinanceTransfer.id.desc())
        .limit(250)
        .all()
    )
    context["account_names"] = {account.id: account.name for account in context["accounts"]}
    return render_template("finance/transfers.html", **context)


@bp.route("/pos-reconciliations", methods=["GET", "POST"])
@permission_required("finance.pos_reconcile.create")
def pos_reconciliations():
    site_id, store_id = _active_scope()
    if request.method == "POST":
        _require_csrf()
        return _commit_action(
            lambda: create_pos_reconciliation(
                site_id=site_id,
                store_id=store_id,
                pos_account_id=_parse_int(request.form.get("pos_account_id")),
                bank_account_id=_parse_int(request.form.get("bank_account_id")),
                gross_amount=_parse_money(request.form.get("gross_amount")),
                commission_rate=_parse_rate(request.form.get("commission_rate")),
                occurred_at=_parse_datetime(request.form.get("occurred_at")),
                reference=request.form.get("reference"),
            ),
            "POS mutabakatı, banka tahsilatı ve komisyonu birlikte kaydedildi.",
            "finance.pos_reconciliations",
        )
    context = _form_context(site_id, store_id)
    context["reconciliations"] = PosReconciliation.query.filter_by(site_id=site_id, store_id=store_id).order_by(PosReconciliation.occurred_at.desc()).limit(100).all()
    return render_template("finance/pos.html", **context)


@bp.get("/current-accounts")
@permission_required("finance.current.view")
def current_accounts():
    site_id, store_id = _active_scope()
    accounts = CurrentAccount.query.filter_by(site_id=site_id).order_by(CurrentAccount.name.asc()).all()
    entries = CurrentEntry.query.filter_by(site_id=site_id, store_id=store_id).order_by(CurrentEntry.status.asc(), CurrentEntry.due_date.asc()).all()
    totals = {}
    for account in accounts:
        account_entries = [entry for entry in entries if entry.current_account_id == account.id]
        totals[account.id] = sum(
            (entry.remaining_amount if entry.entry_type == "receivable" else -entry.remaining_amount for entry in account_entries),
            Decimal("0.00"),
        )
    context = _form_context(site_id, store_id)
    context.update(current_accounts=accounts, entries=entries, current_totals=totals)
    return render_template("finance/current_accounts.html", **context)


@bp.post("/current-accounts/create")
@permission_required("finance.current.manage")
def create_current_account_route():
    _require_csrf()
    site_id, _store_id = _active_scope()
    return _commit_action(
        lambda: create_current_account(
            site_id=site_id,
            account_category=request.form.get("account_category"),
            name=request.form.get("name"),
            tax_no=request.form.get("tax_no"),
            phone=request.form.get("phone"),
            email=request.form.get("email"),
            note=request.form.get("note"),
        ),
        "Cari kart oluşturuldu.",
        "finance.current_accounts",
    )


@bp.post("/current-entries/create")
@permission_required("finance.current.manage")
def create_current_entry_route():
    _require_csrf()
    site_id, store_id = _active_scope()
    return _commit_action(
        lambda: create_current_entry(
            site_id=site_id,
            store_id=store_id,
            current_account_id=_parse_int(request.form.get("current_account_id")),
            entry_type=request.form.get("entry_type"),
            amount=_parse_money(request.form.get("amount")),
            due_date=_parse_date(request.form.get("due_date")),
            description=request.form.get("description"),
        ),
        "Cari borç/alacak kaydı oluşturuldu; kasa henüz etkilenmedi.",
        "finance.current_accounts",
    )


@bp.post("/current-entries/<int:entry_id>/settle")
@permission_required("finance.current.manage")
def settle_current_entry_route(entry_id):
    _require_csrf()
    site_id, store_id = _active_scope()
    return _commit_action(
        lambda: settle_current_entry(
            site_id=site_id,
            store_id=store_id,
            entry_id=entry_id,
            finance_account_id=_parse_int(request.form.get("finance_account_id")),
            amount=_parse_money(request.form.get("amount")),
            occurred_at=_parse_datetime(request.form.get("occurred_at")),
            description=request.form.get("description"),
        ),
        "Cari tahsilat/ödeme kasaya işlendi.",
        "finance.current_accounts",
    )


@bp.get("/obligations")
@permission_required("finance.obligation.view")
def obligations():
    site_id, store_id = _active_scope()
    try:
        created_count = sync_recurring_obligations(
            through_date=now_in_istanbul().date(),
            site_id=site_id,
            store_id=store_id,
        )
        db.session.commit()
        if created_count:
            flash(f"Vadesi gelen {created_count} tekrar dönemi otomatik oluşturuldu.", "success")
    except FinanceConfigurationError as exc:
        db.session.rollback()
        flash(f"Tekrarlayan borçlar güncellenemedi: {exc}", "error")
    context = _form_context(site_id, store_id)
    context["obligations"] = ShortTermObligation.query.filter_by(site_id=site_id, store_id=store_id).order_by(ShortTermObligation.status.asc(), ShortTermObligation.due_date.asc()).all()
    context["recurrence_plans"] = ObligationRecurrencePlan.query.filter_by(
        site_id=site_id,
        store_id=store_id,
    ).order_by(
        ObligationRecurrencePlan.status.asc(),
        ObligationRecurrencePlan.next_due_date.asc(),
    ).all()
    if request.args.get("partial") == "plans":
        return render_template("finance/_obligation_plans_section.html", **context)
    return render_template("finance/obligations.html", **context)


@bp.post("/obligations/create")
@permission_required("finance.obligation.manage")
def create_obligation_route():
    _require_csrf()
    site_id, store_id = _active_scope()
    return _commit_action(
        lambda: create_short_term_obligation(
            site_id=site_id,
            store_id=store_id,
            category_id=_parse_int(request.form.get("category_id")),
            title=request.form.get("title"),
            amount=_parse_money(request.form.get("amount")),
            due_date=_parse_date(request.form.get("due_date")),
            current_account_id=_optional_int(request.form.get("current_account_id")),
            recurrence=request.form.get("recurrence"),
            recurrence_end_date=_parse_date(request.form.get("recurrence_end_date")),
            is_overhead=_parse_overhead_choice(),
            note=request.form.get("note"),
        ),
        "Kısa vadeli borç planlandı; kasa henüz etkilenmedi.",
        "finance.obligations",
    )


@bp.route("/obligation-plans/<int:plan_id>/update", methods=["GET", "POST"])
@permission_required("finance.obligation.manage")
def update_obligation_plan_route(plan_id):
    site_id, store_id = _active_scope()
    plan = ObligationRecurrencePlan.query.filter_by(
        id=plan_id,
        site_id=site_id,
        store_id=store_id,
    ).one_or_none()
    if plan is None:
        abort(404)
    recurrence_labels = _form_context(site_id, store_id)["recurrence_labels"]

    if request.method == "GET":
        if not is_modal_request():
            return redirect(url_for("finance.obligations"))
        return render_template(
            "finance/_obligation_plan_modal.html",
            plan=plan,
            recurrence_labels=recurrence_labels,
        )

    _require_csrf()
    try:
        update_obligation_recurrence_plan(
            site_id=site_id,
            store_id=store_id,
            plan_id=plan_id,
            amount=_parse_money(request.form.get("amount")),
            end_date=_parse_date(request.form.get("end_date")),
        )
        db.session.commit()
    except (FinanceConfigurationError, InvalidOperation, ValueError) as exc:
        db.session.rollback()
        if is_ajax_request():
            plan = ObligationRecurrencePlan.query.filter_by(
                id=plan_id,
                site_id=site_id,
                store_id=store_id,
            ).one_or_none()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": str(exc),
                        "html": render_template(
                            "finance/_obligation_plan_modal.html",
                            plan=plan,
                            recurrence_labels=recurrence_labels,
                        ),
                    }
                ),
                400,
            )
        flash(str(exc), "error")
        return redirect(url_for("finance.obligations"))

    message = "Tekrar planı güncellendi; oluşmuş borçlar değiştirilmedi."
    if is_ajax_request():
        return jsonify(
            {
                "success": True,
                "message": message,
                "refresh_target": "#finance-obligation-plans-section",
                "refresh_url": url_for("finance.obligations", partial="plans"),
            }
        )
    flash(message, "success")
    return redirect(url_for("finance.obligations"))


@bp.post("/obligation-plans/<int:plan_id>/stop")
@permission_required("finance.obligation.manage")
def stop_obligation_plan_route(plan_id):
    _require_csrf()
    site_id, store_id = _active_scope()
    return _commit_action(
        lambda: stop_obligation_recurrence_plan(
            site_id=site_id,
            store_id=store_id,
            plan_id=plan_id,
        ),
        "Tekrar planı durduruldu; oluşmuş borçlar korundu.",
        "finance.obligations",
    )


@bp.post("/obligation-plans/<int:plan_id>/resume")
@permission_required("finance.obligation.manage")
def resume_obligation_plan_route(plan_id):
    _require_csrf()
    site_id, store_id = _active_scope()
    return _commit_action(
        lambda: resume_obligation_recurrence_plan(
            site_id=site_id,
            store_id=store_id,
            plan_id=plan_id,
            resumed_on=now_in_istanbul().date(),
        ),
        "Tekrar planı devam ettirildi; duraklatılan dönemler atlandı.",
        "finance.obligations",
    )


@bp.post("/obligations/<int:obligation_id>/pay")
@permission_required("finance.obligation.manage")
def pay_obligation_route(obligation_id):
    _require_csrf()
    site_id, store_id = _active_scope()
    return _commit_action(
        lambda: pay_short_term_obligation(
            site_id=site_id,
            store_id=store_id,
            obligation_id=obligation_id,
            finance_account_id=_parse_int(request.form.get("finance_account_id")),
            amount=_parse_money(request.form.get("amount")),
            occurred_at=_parse_datetime(request.form.get("occurred_at")),
            description=request.form.get("description"),
        ),
        "Borç ödemesi finans hesabından işlendi.",
        "finance.obligations",
    )


@bp.get("/overheads")
@permission_required("finance.overhead.view")
def overheads():
    site_id, store_id = _active_scope()
    selected_month = _parse_month(request.args.get("month"))
    budgets = MonthlyOverheadBudget.query.filter_by(site_id=site_id, store_id=store_id, budget_month=selected_month).all()
    snapshot = build_finance_snapshot(site_id=site_id, store_ids=[store_id], selected_month=selected_month)
    context = _form_context(site_id, store_id)
    context.update(
        selected_month=selected_month,
        month_options=month_choice_options(selected_month),
        budgets=budgets,
        snapshot=snapshot,
    )
    return render_template("finance/overheads.html", **context)


@bp.post("/overheads")
@permission_required("finance.overhead.manage")
def save_overhead():
    _require_csrf()
    site_id, store_id = _active_scope()
    selected_month = _parse_month(request.form.get("month"))
    response = _commit_action(
        lambda: upsert_monthly_overhead_budget(
            site_id=site_id,
            store_id=store_id,
            budget_month=selected_month,
            category_id=_parse_int(request.form.get("category_id")),
            amount=_parse_money(request.form.get("amount")),
            note=request.form.get("note"),
        ),
        "Aylık genel gider bütçesi güncellendi; kasa hareketi oluşturulmadı.",
        "finance.overheads",
    )
    if response.status_code in {301, 302}:
        if request.form.get("next") == "dashboard":
            response.location = url_for(
                "dashboard.index",
                finance_month=selected_month.strftime("%Y-%m"),
            )
        else:
            response.location = url_for(
                "finance.overheads",
                month=selected_month.strftime("%Y-%m"),
            )
    return response


def _active_scope():
    site_id = get_active_site_id()
    store_id = get_active_store_id()
    store = db.session.get(Store, store_id)
    if store is None or store.site_id != site_id or not store.is_active:
        abort(403)
    return site_id, store_id


def _authorized_store_ids(site_id):
    if not database_authentication_active():
        return [get_active_store_id()]
    return authorized_store_ids(
        user=get_current_user(),
        site_id=site_id,
        role_id=session.get("active_role_id"),
    )


def _selected_store_scope(site_id, active_store_id):
    authorized = _authorized_store_ids(site_id)
    if active_store_id not in authorized:
        abort(403)
    can_show_all = len(authorized) > 1
    show_all = can_show_all and request.args.get("all_stores") == "1"
    return (authorized if show_all else [active_store_id]), show_all, can_show_all


def _form_context(site_id, store_id):
    return {
        "activation": FinanceActivation.query.filter_by(site_id=site_id, store_id=store_id).one_or_none(),
        "accounts": FinanceAccount.query.filter_by(site_id=site_id, store_id=store_id, is_active=True).order_by(FinanceAccount.name.asc()).all(),
        "categories": FinanceCategory.query.filter_by(site_id=site_id, is_active=True).order_by(FinanceCategory.name.asc()).all(),
        "current_accounts": CurrentAccount.query.filter_by(site_id=site_id, is_active=True).order_by(CurrentAccount.name.asc()).all(),
        "current_account_categories": CURRENT_ACCOUNT_CATEGORIES,
        "current_status_labels": {
            "open": "Açık",
            "partial": "Kısmi",
            "closed": "Kapalı",
        },
        "obligation_status_labels": {
            "open": "Açık",
            "partial": "Kısmi",
            "paid": "Ödendi",
        },
        "obligation_plan_status_labels": {
            "active": "Aktif",
            "stopped": "Durduruldu",
            "completed": "Tamamlandı",
        },
        "recurrence_labels": {
            "once": "Tek Sefer",
            "monthly": "Aylık Plan",
            "weekly": "Haftalık Plan",
        },
        "today": date.today(),
        "now_value": now_in_istanbul().strftime("%Y-%m-%dT%H:%M"),
    }


def _commit_action(callback, success_message, endpoint):
    try:
        callback()
        db.session.commit()
        flash(success_message, "success")
    except (FinanceConfigurationError, InvalidOperation, ValueError) as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for(endpoint))


def _require_csrf():
    expected = str(session.get("auth_csrf_token") or "")
    submitted = str(request.form.get("csrf_token") or "")
    if not expected or not compare_digest(expected, submitted):
        abort(400)


def _parse_money(value):
    text = str(value or "").strip().replace("₺", "").replace(" ", "")
    if not text:
        raise FinanceConfigurationError("Tutar zorunludur.")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return Decimal(text)


def _parse_rate(value):
    text = str(value or "").strip().replace("%", "").replace(" ", "")
    if not text:
        raise FinanceConfigurationError("Komisyon oranı zorunludur.")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return Decimal(text)


def _parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise FinanceConfigurationError("Geçerli bir kayıt seçmelisiniz.") from exc


def _optional_int(value):
    return _parse_int(value) if str(value or "").strip() else None


def _parse_overhead_choice():
    if request.form.get("is_overhead_mode") == "default":
        return None
    return request.form.get("is_overhead") == "1"


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise FinanceConfigurationError("Tarih geçerli değil.") from exc


def _parse_datetime(value):
    if not value:
        return datetime.utcnow()
    try:
        return istanbul_to_utc(datetime.fromisoformat(str(value)))
    except ValueError as exc:
        raise FinanceConfigurationError("Tarih/saat geçerli değil.") from exc


def _parse_month(value):
    if not value:
        return date.today().replace(day=1)
    try:
        return date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise FinanceConfigurationError("Ay bilgisi geçerli değil.") from exc
