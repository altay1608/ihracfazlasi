"""Atomic compensating entries. Original documents are never deleted."""
from datetime import datetime
from app.extensions import db
from app.models import Sale, CreditSaleCollection, ExpenseVoucher
from app.models.finance import FinanceMovement, FinanceTransfer, PosReconciliation
from app.services.finance import FinanceConfigurationError, reverse_movement, ensure_finance_period_open, credit_sale_summary


def cancelled_collection_ids(site_id, store_id, ids=None):
    query = db.session.query(CreditSaleCollection.id).join(FinanceMovement,
        FinanceMovement.source_id == CreditSaleCollection.finance_transfer_id).filter(
        CreditSaleCollection.site_id == site_id, CreditSaleCollection.store_id == store_id,
        FinanceMovement.site_id == site_id, FinanceMovement.store_id == store_id,
        FinanceMovement.source_type == "transfer", FinanceMovement.reversal_of_id.isnot(None))
    if ids is not None:
        if not ids:
            return set()
        query = query.filter(CreditSaleCollection.id.in_(ids))
    return {row[0] for row in query.distinct().all()}


def _reverse_transfer(transfer, reason, when):
    originals = FinanceMovement.query.filter_by(site_id=transfer.site_id, store_id=transfer.store_id,
        source_type="transfer", source_id=transfer.id, reversal_of_id=None).order_by(FinanceMovement.id).all()
    if len(originals) != 2 or originals[0].amount != originals[1].amount or {row.direction for row in originals} != {"in", "out"}:
        raise FinanceConfigurationError("Transfer çifti doğrulanamadı; kayıt değiştirilmedi.")
    for movement in originals:
        reverse_movement(movement, reason, when)


def cancel_finance_document(site_id, store_id, kind, record_id, reason):
    reason = str(reason or "").strip()
    if not 5 <= len(reason) <= 400:
        raise FinanceConfigurationError("İptal nedeni 5–400 karakter olmalıdır.")
    when = datetime.utcnow()
    ensure_finance_period_open(site_id, store_id, when)
    if kind == "transfer":
        transfer = FinanceTransfer.query.filter_by(id=record_id, site_id=site_id, store_id=store_id).with_for_update().one_or_none()
        if transfer is None:
            raise FinanceConfigurationError("Transfer bulunamadı.")
        if CreditSaleCollection.query.filter_by(finance_transfer_id=transfer.id).first():
            raise FinanceConfigurationError("Bu kayıt veresiye tahsilatına bağlı; Tahsilat sekmesinden iptal edin.")
        _reverse_transfer(transfer, reason, when)
    elif kind == "collection":
        collection = CreditSaleCollection.query.filter_by(id=record_id, site_id=site_id, store_id=store_id).one_or_none()
        if collection is None:
            raise FinanceConfigurationError("Tahsilat bulunamadı.")
        # Same lock as new collections, so balance/status cannot race.
        sale = Sale.query.filter_by(id=collection.sale_id, site_id=site_id, store_id=store_id).with_for_update().one()
        if collection.id in cancelled_collection_ids(site_id, store_id, [collection.id]):
            return
        pos = PosReconciliation.query.filter_by(id=collection.pos_reconciliation_id,
            site_id=site_id, store_id=store_id).with_for_update().one_or_none() if collection.pos_reconciliation_id else None
        if pos and pos.status == "settled":
            raise FinanceConfigurationError("Bankaya geçmiş kart tahsilatı otomatik iptal edilemez; önce banka iadesini doğrulayın.")
        transfer = FinanceTransfer.query.filter_by(id=collection.finance_transfer_id,
            site_id=site_id, store_id=store_id).with_for_update().one()
        _reverse_transfer(transfer, reason, when)
        for movement in FinanceMovement.query.filter_by(site_id=site_id, store_id=store_id,
            source_type="credit_collection", source_id=collection.id, reversal_of_id=None).all():
            reverse_movement(movement, reason, when)
        if pos:
            pos.status = "cancelled"
        db.session.flush()
        summary = credit_sale_summary(sale)
        sale.payment_status = "PAID" if summary["remaining"] == 0 else ("PARTIAL" if summary["collected"] > 0 else "OPEN")
        for payment in sale.payments:
            if payment.payment_method == "Veresiye":
                payment.status = sale.payment_status
    elif kind == "expense":
        expense = ExpenseVoucher.query.filter_by(id=record_id, site_id=site_id, store_id=store_id).with_for_update().one_or_none()
        if expense is None or expense.status != "approved" or not expense.movement_id:
            raise FinanceConfigurationError("Yalnızca onaylı masraf için ters kayıt oluşturulabilir.")
        movement = FinanceMovement.query.filter_by(id=expense.movement_id, site_id=site_id, store_id=store_id).one()
        reverse_movement(movement, reason, when)
        # Preserve the original voucher and its historical approval; correction is in the ledger.
    else:
        raise FinanceConfigurationError("Desteklenmeyen işlem türü.")
