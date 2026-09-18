import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import (
    FinanceAccount,
    FinanceActivation,
    FinanceApproval,
    FinanceCategory,
    FinanceMovement,
    FinancePaymentMapping,
    PosReconciliation,
    CurrentAccount,
    DailyCashClosing,
    ExpenseVoucher,
    Package,
    PersonnelAdvanceSettlement,
    Product,
    Sale,
    Site,
    Store,
    StoreInventory,
    SupplierInvoice,
)
from app.services.finance import (
    activate_finance,
    create_manual_movement,
    get_account_balance,
    settle_auto_pos_reconciliation,
    sync_sale_finance,
    update_pos_settings,
)
from app.services.finance_operations import (
    create_daily_closing,
    create_expense,
    create_personnel_record,
    create_supplier_invoice,
    decide_approval,
    settle_personnel_advance,
)
from config import BaseConfig


class FinanceModuleTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parent / f"_finance_{uuid4().hex}.db"
        self.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.database_path.as_posix()}"
        self.app = create_app("development")
        self.app.config.update(TESTING=True, AUTH_ENABLED=False)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        package = Package(code="PRO", name="Pro")
        self.site = Site(code="FIN", name="Finans Test", package=package, is_sandbox=False)
        self.store = Store(code="MERKEZ", name="Merkez", site=self.site)
        db.session.add_all([package, self.site, self.store])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()
        BaseConfig.SQLALCHEMY_DATABASE_URI = self.old_database_uri
        self.database_path.unlink(missing_ok=True)

    def test_activation_sale_and_manual_expense_update_the_ledger(self):
        activated_at = datetime.utcnow() - timedelta(minutes=1)
        activate_finance(
            self.site.id,
            self.store.id,
            opening_cash=Decimal("100.00"),
            activated_at=activated_at,
        )
        db.session.flush()

        sale = Sale(
            document_no=1,
            site_id=self.site.id,
            store_id=self.store.id,
            sale_date=datetime.utcnow(),
            total_amount=Decimal("250.00"),
            payment_method="Nakit",
        )
        db.session.add(sale)
        sync_sale_finance(sale)

        cash = FinanceAccount.query.filter_by(
            site_id=self.site.id,
            store_id=self.store.id,
            code="CASH",
        ).one()
        expense = FinanceCategory.query.filter_by(site_id=self.site.id, code="MANUAL_OUT").one()
        create_manual_movement(
            site_id=self.site.id,
            store_id=self.store.id,
            account_id=cash.id,
            category_id=expense.id,
            direction="out",
            amount=Decimal("30.00"),
            occurred_at=datetime.utcnow(),
            description="Test mağaza gideri",
            is_overhead=True,
        )
        db.session.commit()

        self.assertEqual(get_account_balance(cash), Decimal("320.00"))
        self.assertEqual(FinanceMovement.query.filter_by(source_type="sale").count(), 1)
        self.assertEqual(FinanceMovement.query.filter_by(movement_type="manual").count(), 1)

    def test_first_sale_automatically_starts_finance_and_posts_revenue(self):
        sale = Sale(
            document_no=1,
            site_id=self.site.id,
            store_id=self.store.id,
            sale_date=datetime.utcnow(),
            total_amount=Decimal("425.00"),
            payment_method="Nakit",
        )
        db.session.add(sale)

        movement_id = sync_sale_finance(sale)
        db.session.commit()

        activation = FinanceActivation.query.filter_by(
            site_id=self.site.id,
            store_id=self.store.id,
        ).one()
        movement = db.session.get(FinanceMovement, movement_id)
        self.assertIsNotNone(activation)
        self.assertEqual(movement.movement_type, "sale")
        self.assertEqual(movement.amount, Decimal("425.00"))
        self.assertEqual(movement.source_id, sale.id)

    def test_card_sale_deducts_commission_and_waits_for_next_day_bank_settlement(self):
        sale_time = datetime(2026, 9, 16, 9, 0)
        sale = Sale(
            document_no=20,
            site_id=self.site.id,
            store_id=self.store.id,
            sale_date=sale_time,
            total_amount=Decimal("2000.00"),
            payment_method="Kredi Kartı",
        )
        db.session.add(sale)

        sync_sale_finance(sale)
        db.session.commit()

        pos = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code="POS").one()
        bank = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code="BANK").one()
        reconciliation = PosReconciliation.query.filter_by(sale_id=sale.id).one()
        self.assertEqual(reconciliation.status, "pending")
        self.assertTrue(reconciliation.auto_generated)
        self.assertEqual(reconciliation.gross_amount, Decimal("2000.00"))
        self.assertEqual(reconciliation.commission_amount, Decimal("56.10"))
        self.assertEqual(reconciliation.commission_vat_amount, Decimal("5.10"))
        self.assertEqual(reconciliation.net_amount, Decimal("1943.90"))
        self.assertEqual(reconciliation.expected_settlement_date, date(2026, 9, 17))
        self.assertEqual(get_account_balance(pos), Decimal("1943.90"))
        self.assertEqual(get_account_balance(bank), Decimal("0.00"))

        settle_auto_pos_reconciliation(
            site_id=self.site.id,
            store_id=self.store.id,
            reconciliation_id=reconciliation.id,
            settled_at=datetime(2026, 9, 17, 9, 0),
        )
        db.session.commit()

        self.assertEqual(reconciliation.status, "settled")
        self.assertEqual(get_account_balance(pos), Decimal("0.00"))
        self.assertEqual(get_account_balance(bank), Decimal("1943.90"))
        self.assertEqual(FinanceMovement.query.filter_by(movement_type="pos_commission").count(), 1)

    def test_cash_sale_does_not_create_pos_commission_or_settlement(self):
        sale = Sale(
            document_no=21,
            site_id=self.site.id,
            store_id=self.store.id,
            sale_date=datetime.utcnow(),
            total_amount=Decimal("750.00"),
            payment_method="Nakit",
        )
        db.session.add(sale)
        sync_sale_finance(sale)
        db.session.commit()

        self.assertEqual(PosReconciliation.query.count(), 0)
        self.assertEqual(FinanceMovement.query.filter_by(movement_type="pos_commission").count(), 0)

    def test_bank_transfer_sale_never_creates_commission_and_repairs_legacy_pos_mapping(self):
        activate_finance(
            self.site.id,
            self.store.id,
            activated_at=datetime.utcnow() - timedelta(minutes=1),
        )
        db.session.flush()
        bank = FinanceAccount.query.filter_by(
            site_id=self.site.id,
            store_id=self.store.id,
            code="BANK",
        ).one()
        pos = FinanceAccount.query.filter_by(
            site_id=self.site.id,
            store_id=self.store.id,
            code="POS",
        ).one()
        transfer_mapping = FinancePaymentMapping.query.filter_by(
            site_id=self.site.id,
            store_id=self.store.id,
            payment_method="Havale/EFT",
        ).one()
        transfer_mapping.account_id = pos.id
        db.session.flush()

        sale = Sale(
            document_no=24,
            site_id=self.site.id,
            store_id=self.store.id,
            sale_date=datetime.utcnow(),
            total_amount=Decimal("2000.00"),
            payment_method="Havale/EFT",
        )
        db.session.add(sale)
        sync_sale_finance(sale)
        db.session.commit()

        self.assertEqual(transfer_mapping.account_id, bank.id)
        self.assertEqual(get_account_balance(bank), Decimal("2000.00"))
        self.assertEqual(get_account_balance(pos), Decimal("0.00"))
        self.assertEqual(PosReconciliation.query.count(), 0)
        self.assertEqual(FinanceMovement.query.filter_by(movement_type="pos_commission").count(), 0)

    def test_pos_settings_change_future_commission_and_settlement_day(self):
        activate_finance(
            self.site.id,
            self.store.id,
            activated_at=datetime(2026, 9, 16, 8, 0),
        )
        db.session.flush()
        bank = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code="BANK").one()
        update_pos_settings(
            site_id=self.site.id,
            store_id=self.store.id,
            commission_rate=Decimal("3.1000"),
            settlement_days=2,
            bank_account_id=bank.id,
        )
        sale = Sale(
            document_no=22,
            site_id=self.site.id,
            store_id=self.store.id,
            sale_date=datetime(2026, 9, 16, 9, 0),
            total_amount=Decimal("2000.00"),
            payment_method="Kredi Kartı",
        )
        db.session.add(sale)
        sync_sale_finance(sale)
        db.session.commit()

        reconciliation = PosReconciliation.query.filter_by(sale_id=sale.id).one()
        self.assertEqual(reconciliation.commission_amount, Decimal("68.20"))
        self.assertEqual(reconciliation.commission_vat_amount, Decimal("6.20"))
        self.assertEqual(reconciliation.net_amount, Decimal("1931.80"))
        self.assertEqual(reconciliation.expected_settlement_date, date(2026, 9, 18))

    def test_repeated_card_sale_sync_is_idempotent(self):
        sale = Sale(
            document_no=23,
            site_id=self.site.id,
            store_id=self.store.id,
            sale_date=datetime.utcnow(),
            total_amount=Decimal("1000.00"),
            payment_method="Kredi Kartı",
        )
        db.session.add(sale)
        sync_sale_finance(sale)
        sync_sale_finance(sale)
        db.session.commit()

        self.assertEqual(PosReconciliation.query.filter_by(sale_id=sale.id).count(), 1)
        self.assertEqual(FinanceMovement.query.filter_by(source_type="sale", source_id=sale.id).count(), 2)

    def test_staff_workflows_close_the_day_and_apply_approval_limit(self):
        activate_finance(self.site.id, self.store.id, opening_cash=Decimal("10000.00"))
        db.session.flush()
        cash = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code="CASH").one()
        expense_category = FinanceCategory.query.filter_by(site_id=self.site.id, code="MANUAL_OUT").one()

        approved = create_expense(
            site_id=self.site.id, store_id=self.store.id, account_id=cash.id,
            category_id=expense_category.id, expense_date=date.today(), vendor="Kırtasiye",
            document_no="F-1", description="Ofis malzemesi", net_amount=100,
            vat_amount=20, config={"FINANCE_APPROVAL_LIMIT": "5000"},
        )
        pending = create_expense(
            site_id=self.site.id, store_id=self.store.id, account_id=cash.id,
            category_id=expense_category.id, expense_date=date.today(), vendor="Dekorasyon",
            document_no="F-2", description="Mağaza düzenlemesi", net_amount=6000,
            vat_amount=0, config={"FINANCE_APPROVAL_LIMIT": "5000"},
        )
        db.session.flush()
        approval = FinanceApproval.query.filter_by(entity_type="expense", entity_id=pending.id).one()
        decide_approval(approval, approve=True, note="Bütçeye uygun")
        closing = create_daily_closing(
            site_id=self.site.id, store_id=self.store.id, business_date=date.today(),
            counted_cash=Decimal("3875.00"), counted_card=0, counted_transfer=0,
            handover_from="Personel A", handover_to="Personel B",
        )
        db.session.commit()

        self.assertEqual(closing.cash_difference, Decimal("-5.00"))
        self.assertEqual(approved.status, "approved")
        self.assertEqual(pending.status, "approved")
        self.assertEqual(approval.status, "approved")
        self.assertEqual(ExpenseVoucher.query.count(), 2)
        self.assertEqual(DailyCashClosing.query.count(), 1)

        with self.assertRaisesRegex(ValueError, "kapatılmış"):
            create_expense(
                site_id=self.site.id, store_id=self.store.id, account_id=cash.id,
                category_id=expense_category.id, expense_date=date.today(), vendor="Geç Kayıt",
                document_no="F-3", description="Kapanış sonrası", net_amount=10,
                vat_amount=0, config={"FINANCE_APPROVAL_LIMIT": "5000"},
            )

    def test_supplier_invoice_creates_open_payable(self):
        activate_finance(self.site.id, self.store.id)
        supplier = CurrentAccount(
            site_id=self.site.id, code="32000001", account_category="supplier", name="Test Tedarikçi"
        )
        db.session.add(supplier)
        product = Product(
            site_id=self.site.id, name="Test Gömlek", category="Gömlek",
            barcode="FIN-001", product_code="FIN001", purchase_price=100, sale_price=200,
        )
        db.session.add(product)
        db.session.flush()
        invoice = create_supplier_invoice(
            site_id=self.site.id, store_id=self.store.id, supplier_id=supplier.id,
            invoice_no="ALIS-1", invoice_date=date.today(), due_date=date.today(),
            net_amount=750, vat_amount=75,
            line_items=[{"product_id": product.id, "quantity": 3, "unit_cost": 250}],
        )
        db.session.commit()

        self.assertEqual(SupplierInvoice.query.count(), 1)
        self.assertEqual(invoice.current_entry.entry_type, "payable")
        self.assertEqual(invoice.current_entry.remaining_amount, Decimal("825.00"))
        inventory = StoreInventory.query.filter_by(store_id=self.store.id, product_id=product.id).one()
        self.assertEqual(inventory.stock_quantity, 3)
        self.assertEqual(len(invoice.lines), 1)

    def test_supplier_invoice_rejects_stock_total_mismatch(self):
        activate_finance(self.site.id, self.store.id)
        supplier = CurrentAccount(
            site_id=self.site.id, code="32000002", account_category="supplier", name="Kontrollü Tedarikçi"
        )
        product = Product(
            site_id=self.site.id, name="Kontrollü Ürün", category="Gömlek",
            barcode="FIN-002", product_code="FIN002", purchase_price=100, sale_price=200,
        )
        db.session.add_all([supplier, product])
        db.session.flush()

        with self.assertRaisesRegex(ValueError, "uyuşmuyor"):
            create_supplier_invoice(
                site_id=self.site.id, store_id=self.store.id, supplier_id=supplier.id,
                invoice_no="ALIS-2", invoice_date=date.today(), due_date=date.today(),
                net_amount=1000, vat_amount=100,
                line_items=[{"product_id": product.id, "quantity": 3, "unit_cost": 250}],
            )
        db.session.rollback()

    def test_personnel_advance_can_be_partially_settled(self):
        activate_finance(self.site.id, self.store.id, opening_cash=Decimal("1000.00"))
        db.session.flush()
        cash = FinanceAccount.query.filter_by(site_id=self.site.id, store_id=self.store.id, code="CASH").one()
        record = create_personnel_record(
            site_id=self.site.id, store_id=self.store.id, personnel_name="Personel A",
            record_type="advance", account_id=cash.id, amount=100,
            occurred_on=date.today(), description="Yol avansı",
            config={"FINANCE_APPROVAL_LIMIT": "5000"},
        )
        settle_personnel_advance(
            record=record, amount=40, settlement_type="cash_return",
            account_id=cash.id, description="Kısmi iade",
        )
        db.session.commit()

        self.assertEqual(record.remaining_amount, Decimal("60.00"))
        self.assertEqual(PersonnelAdvanceSettlement.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
