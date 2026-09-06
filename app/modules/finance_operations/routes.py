from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, session, url_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    CurrentAccount,
    CurrentEntry,
    DailyCashClosing,
    ExpenseVoucher,
    FinanceAccount,
    FinanceApproval,
    FinanceCategory,
    PersonnelFinanceRecord,
    Product,
    SupplierInvoice,
)
from app.services.access_control import permission_required
from app.services.finance_operations import (
    closing_expectations,
    create_daily_closing,
    create_expense,
    create_personnel_record,
    create_supplier_invoice,
    decide_approval,
    reopen_daily_closing,
    settle_personnel_advance,
)
from app.services.identity_access import get_active_site_id, get_active_store_id
from app.utils import now_in_istanbul, quantize_amount


bp = Blueprint("finance_ops", __name__, url_prefix="/finance/operations")
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024


def _scope():
    return get_active_site_id(), get_active_store_id()


def _csrf():
    if not session.get("auth_csrf_token") or request.form.get("csrf_token") != session.get("auth_csrf_token"):
        abort(400)


def _date(value, fallback=None):
    try:
        return date.fromisoformat(value) if value else (fallback or now_in_istanbul().date())
    except ValueError as exc:
        raise ValueError("Tarih geçerli değil.") from exc


def _money(value):
    text = str(value or "0").strip().replace("₺", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return quantize_amount(Decimal(text))


def _attachment(upload):
    if upload is None or not upload.filename:
        return {}
    data = upload.read(MAX_DOCUMENT_BYTES + 1)
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValueError("Belge en fazla 5 MB olabilir.")
    mime = str(upload.mimetype or "").lower()
    if mime not in ALLOWED_DOCUMENT_TYPES:
        raise ValueError("Yalnız PDF, JPG, PNG veya WEBP belge yükleyebilirsiniz.")
    return {"attachment_name": upload.filename[:255], "attachment_mime": mime, "attachment_data": data}


def _form_options(site_id, store_id):
    return {
        "accounts": FinanceAccount.query.filter_by(site_id=site_id, store_id=store_id, is_active=True).order_by(FinanceAccount.name).all(),
        "expense_categories": FinanceCategory.query.filter(
            FinanceCategory.site_id == site_id,
            FinanceCategory.is_active.is_(True),
            FinanceCategory.direction.in_(("out", "both")),
        ).order_by(FinanceCategory.name).all(),
        "suppliers": CurrentAccount.query.filter_by(site_id=site_id, account_category="supplier", is_active=True).order_by(CurrentAccount.name).all(),
        "products": Product.query.filter_by(site_id=site_id).order_by(Product.name).all(),
        "today": now_in_istanbul().date(),
    }


@bp.get("/")
@permission_required("finance.ledger.view")
def dashboard():
    site_id, store_id = _scope()
    today = now_in_istanbul().date()
    accounts = FinanceAccount.query.filter_by(site_id=site_id, store_id=store_id, is_active=True).all()
    balances = []
    from app.services.finance import get_account_balance
    for account in accounts:
        balances.append({"account": account, "balance": get_account_balance(account)})
    pending_approvals = FinanceApproval.query.filter_by(site_id=site_id, store_id=store_id, status="pending").count()
    open_payables = db.session.query(func.coalesce(func.sum(CurrentEntry.remaining_amount), 0)).filter_by(
        site_id=site_id, store_id=store_id, entry_type="payable"
    ).scalar()
    payable_base = [
        CurrentEntry.site_id == site_id,
        CurrentEntry.store_id == store_id,
        CurrentEntry.entry_type == "payable",
        CurrentEntry.remaining_amount > 0,
    ]
    def payable_sum(*conditions):
        return db.session.query(func.coalesce(func.sum(CurrentEntry.remaining_amount), 0)).filter(
            *payable_base, *conditions
        ).scalar()
    payable_aging = {
        "overdue": payable_sum(CurrentEntry.due_date < today),
        "next_7": payable_sum(CurrentEntry.due_date >= today, CurrentEntry.due_date <= today + timedelta(days=7)),
        "next_30": payable_sum(CurrentEntry.due_date > today + timedelta(days=7), CurrentEntry.due_date <= today + timedelta(days=30)),
    }
    recent_expenses = ExpenseVoucher.query.filter_by(site_id=site_id, store_id=store_id).order_by(ExpenseVoucher.created_at.desc()).limit(5).all()
    recent_closing = DailyCashClosing.query.filter_by(site_id=site_id, store_id=store_id).order_by(DailyCashClosing.business_date.desc()).first()
    return render_template(
        "finance_operations/dashboard.html", balances=balances,
        pending_approvals=pending_approvals, open_payables=open_payables,
        recent_expenses=recent_expenses, recent_closing=recent_closing,
        expectations=closing_expectations(site_id, store_id, today), payable_aging=payable_aging, today=today,
    )


@bp.route("/daily-closing", methods=["GET", "POST"])
@permission_required("finance.accounts.manage")
def daily_closing():
    site_id, store_id = _scope()
    selected_date = _date(request.values.get("business_date"))
    if request.method == "POST":
        _csrf()
        try:
            create_daily_closing(
                site_id=site_id, store_id=store_id, business_date=selected_date,
                counted_cash=_money(request.form.get("counted_cash")),
                counted_card=_money(request.form.get("counted_card")),
                counted_transfer=_money(request.form.get("counted_transfer")),
                handover_from=request.form.get("handover_from"),
                handover_to=request.form.get("handover_to"), note=request.form.get("note"),
            )
            db.session.commit()
            flash("Gün sonu kapanışı tamamlandı ve kilitlendi.", "success")
            return redirect(url_for("finance_ops.daily_closing"))
        except (TypeError, ValueError, InvalidOperation) as exc:
            db.session.rollback()
            flash(str(exc), "error")
    closings = DailyCashClosing.query.filter_by(site_id=site_id, store_id=store_id).order_by(DailyCashClosing.business_date.desc()).limit(60).all()
    return render_template(
        "finance_operations/daily_closing.html", closings=closings,
        expectations=closing_expectations(site_id, store_id, selected_date),
        selected_date=selected_date,
    )


@bp.post("/daily-closing/<int:closing_id>/reopen")
@permission_required("finance.accounts.manage")
def daily_closing_reopen(closing_id):
    _csrf()
    site_id, store_id = _scope()
    closing = DailyCashClosing.query.filter_by(
        id=closing_id, site_id=site_id, store_id=store_id
    ).first_or_404()
    try:
        reopen_daily_closing(closing, request.form.get("reason"))
        db.session.commit()
        flash("Gün yeniden açıldı. Düzeltme işlemlerinden sonra tekrar kapatın.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for("finance_ops.daily_closing", business_date=closing.business_date.isoformat()))


@bp.route("/expenses", methods=["GET", "POST"])
@permission_required("finance.manual.create")
def expenses():
    site_id, store_id = _scope()
    if request.method == "POST":
        _csrf()
        try:
            voucher = create_expense(
                site_id=site_id, store_id=store_id,
                account_id=int(request.form.get("account_id")),
                category_id=int(request.form.get("category_id")),
                expense_date=_date(request.form.get("expense_date")),
                vendor=request.form.get("vendor"), document_no=request.form.get("document_no"),
                description=request.form.get("description"), net_amount=_money(request.form.get("net_amount")),
                vat_amount=_money(request.form.get("vat_amount")), config=current_app.config,
            )
            for key, value in _attachment(request.files.get("attachment")).items():
                setattr(voucher, key, value)
            db.session.commit()
            flash("Masraf kaydedildi." if voucher.status == "approved" else "Masraf yönetici onayına gönderildi.", "success")
            return redirect(url_for("finance_ops.expenses"))
        except IntegrityError:
            db.session.rollback()
            flash("Masraf kaydı veritabanındaki mevcut bir kayıtla çakıştı. Bilgileri kontrol edin.", "error")
        except (TypeError, ValueError, InvalidOperation) as exc:
            db.session.rollback()
            flash(str(exc), "error")
    vouchers = ExpenseVoucher.query.filter_by(site_id=site_id, store_id=store_id).order_by(ExpenseVoucher.expense_date.desc(), ExpenseVoucher.id.desc()).limit(200).all()
    return render_template("finance_operations/expenses.html", vouchers=vouchers, **_form_options(site_id, store_id))


@bp.route("/supplier-invoices", methods=["GET", "POST"])
@permission_required("finance.current.manage")
def supplier_invoices():
    site_id, store_id = _scope()
    if request.method == "POST":
        _csrf()
        try:
            invoice = create_supplier_invoice(
                site_id=site_id, store_id=store_id, supplier_id=int(request.form.get("supplier_id")),
                invoice_no=request.form.get("invoice_no"), invoice_date=_date(request.form.get("invoice_date")),
                due_date=_date(request.form.get("due_date"), None) if request.form.get("due_date") else None,
                net_amount=_money(request.form.get("net_amount")), vat_amount=_money(request.form.get("vat_amount")),
                note=request.form.get("note"),
                line_items=[
                    {"product_id": product_id, "quantity": quantity, "unit_cost": unit_cost}
                    for product_id, quantity, unit_cost in zip(
                        request.form.getlist("product_id"),
                        request.form.getlist("quantity"),
                        request.form.getlist("unit_cost"),
                    )
                    if product_id
                ],
            )
            for key, value in _attachment(request.files.get("attachment")).items():
                setattr(invoice, key, value)
            db.session.commit()
            flash("Alış faturası, tedarikçi borcu ve stok girişi kaydedildi.", "success")
            return redirect(url_for("finance_ops.supplier_invoices"))
        except IntegrityError:
            db.session.rollback()
            flash("Bu fatura numarası daha önce kaydedilmiş olabilir. Fatura bilgilerini kontrol edin.", "error")
        except (TypeError, ValueError, InvalidOperation) as exc:
            db.session.rollback()
            flash(str(exc), "error")
    invoices = SupplierInvoice.query.filter_by(site_id=site_id, store_id=store_id).order_by(SupplierInvoice.invoice_date.desc()).limit(200).all()
    return render_template("finance_operations/supplier_invoices.html", invoices=invoices, **_form_options(site_id, store_id))


@bp.route("/personnel", methods=["GET", "POST"])
@permission_required("finance.manual.create")
def personnel():
    site_id, store_id = _scope()
    if request.method == "POST":
        _csrf()
        try:
            record = create_personnel_record(
                site_id=site_id, store_id=store_id, personnel_name=request.form.get("personnel_name"),
                record_type=request.form.get("record_type"), account_id=int(request.form.get("account_id")),
                amount=_money(request.form.get("amount")), occurred_on=_date(request.form.get("occurred_on")),
                description=request.form.get("description"), config=current_app.config,
            )
            for key, value in _attachment(request.files.get("attachment")).items():
                setattr(record, key, value)
            db.session.commit()
            flash("Personel işlemi kaydedildi." if record.status == "approved" else "Personel işlemi onaya gönderildi.", "success")
            return redirect(url_for("finance_ops.personnel"))
        except (TypeError, ValueError, InvalidOperation) as exc:
            db.session.rollback()
            flash(str(exc), "error")
    records = PersonnelFinanceRecord.query.filter_by(site_id=site_id, store_id=store_id).order_by(PersonnelFinanceRecord.occurred_on.desc()).limit(200).all()
    return render_template("finance_operations/personnel.html", records=records, **_form_options(site_id, store_id))


@bp.post("/personnel/<int:record_id>/settle")
@permission_required("finance.accounts.manage")
def personnel_settle(record_id):
    _csrf()
    site_id, store_id = _scope()
    record = PersonnelFinanceRecord.query.filter_by(id=record_id, site_id=site_id, store_id=store_id).first_or_404()
    try:
        settle_personnel_advance(
            record=record, amount=_money(request.form.get("amount")),
            settlement_type=request.form.get("settlement_type"),
            account_id=int(request.form.get("account_id")), description=request.form.get("description"),
        )
        db.session.commit()
        flash("Personel avansı mahsuplaştırıldı.", "success")
    except (TypeError, ValueError, InvalidOperation) as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for("finance_ops.personnel"))


@bp.get("/approvals")
@permission_required("finance.accounts.manage")
def approvals():
    site_id, store_id = _scope()
    rows = FinanceApproval.query.filter_by(site_id=site_id, store_id=store_id).order_by(FinanceApproval.created_at.desc()).limit(200).all()
    return render_template("finance_operations/approvals.html", approvals=rows)


@bp.post("/approvals/<int:approval_id>/decide")
@permission_required("finance.accounts.manage")
def approval_decide(approval_id):
    _csrf()
    site_id, store_id = _scope()
    approval = FinanceApproval.query.filter_by(id=approval_id, site_id=site_id, store_id=store_id).first_or_404()
    try:
        decide_approval(approval, approve=request.form.get("decision") == "approve", note=request.form.get("note"))
        db.session.commit()
        flash("Onay talebi sonuçlandırıldı.", "success")
    except (TypeError, ValueError, InvalidOperation) as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for("finance_ops.approvals"))


@bp.get("/documents/<string:kind>/<int:record_id>")
@permission_required("finance.ledger.view")
def document(kind, record_id):
    site_id, store_id = _scope()
    model = {"expense": ExpenseVoucher, "invoice": SupplierInvoice, "personnel": PersonnelFinanceRecord}.get(kind)
    if model is None:
        abort(404)
    record = model.query.filter_by(id=record_id, site_id=site_id, store_id=store_id).first_or_404()
    if not record.attachment_data:
        abort(404)
    return send_file(BytesIO(record.attachment_data), mimetype=record.attachment_mime,
                     download_name=record.attachment_name, as_attachment=True)
