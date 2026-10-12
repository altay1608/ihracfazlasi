import unittest
from datetime import date, datetime
from unittest.mock import patch

from sqlalchemy import event

from app import create_app
from app.extensions import db
from app.models.finance import FinanceAccount, FinanceCategory, FinanceMovement
from app.services.lobby_finance import build_lobby_finance
from app.services.finance_reporting import build_finance_snapshot
from app.utils import istanbul_to_utc
from config import BaseConfig


class LobbyFinanceTests(unittest.TestCase):
    def setUp(self):
        with patch.object(BaseConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"):
            self.app = create_app("development")
        self.app.config.update(TESTING=True, AUTH_ENABLED=False, AUDIT_LOGGING_ENABLED=False)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.cash = FinanceAccount(site_id=1, store_id=1, code="cash", name="Nakit", account_type="cash")
        self.category = FinanceCategory(site_id=1, code="expense", name="Kargo", direction="both")
        db.session.add_all([self.cash, self.category])
        db.session.flush()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def movement(self, amount=100, direction="out", kind="manual", **kwargs):
        row = FinanceMovement(account_id=self.cash.id, category_id=self.category.id,
            site_id=kwargs.pop("site_id", 1), store_id=kwargs.pop("store_id", 1),
            occurred_at=kwargs.pop("occurred_at", istanbul_to_utc(datetime(2026, 10, 12, 12))),
            amount=amount, direction=direction, movement_type=kind, source_type="test",
            source_key=str(db.session.query(FinanceMovement).count()), **kwargs)
        db.session.add(row)
        db.session.flush()
        return row

    def summary(self):
        return build_lobby_finance(1, 1, date(2026, 10, 12))

    def test_expense_reversal_and_scope(self):
        original = self.movement()
        self.movement(direction="in", kind="reversal", reversal_of_id=original.id)
        self.movement(25)
        self.movement(900, store_id=2)
        self.movement(800, site_id=2)
        self.movement(700, occurred_at=istanbul_to_utc(datetime(2026, 9, 30, 23, 59)))
        self.movement(600, occurred_at=istanbul_to_utc(datetime(2026, 10, 13)))
        result = self.summary()
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["amount"], 25)
        self.assertEqual(len(result["recent"]), 3)
        self.assertEqual(result["recent"][0]["date"], "12.10.2026 12:00")

    def test_transfer_and_debt_are_not_expenses(self):
        self.movement(300, kind="transfer")
        self.movement(300, direction="in", kind="transfer")
        self.movement(400, kind="current_settlement")
        self.movement(10, kind="pos_commission")
        result = self.summary()
        self.assertEqual(len(result["rows"]), 4)
        self.assertNotIn("Gider", [row["title"] for row in result["rows"]])
        self.assertIn("Cari borç ödemesi", [row["title"] for row in result["rows"]])

    def test_query_count_bounded_and_recent_limited(self):
        for _ in range(25):
            self.movement()
        statements = []
        def record(*args):
            statements.append(args[2])
        event.listen(db.engine, "before_cursor_execute", record)
        try:
            result = self.summary()
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
        self.assertEqual(len(statements), 2)
        self.assertEqual(len(result["recent"]), 5)
        self.assertEqual(result["rows"][0]["amount"], 2500)

    def test_prior_month_expense_correction_and_overhead_label(self):
        original = self.movement(100, is_overhead=True,
            occurred_at=istanbul_to_utc(datetime(2026, 9, 30, 23)))
        self.movement(100, direction="in", kind="reversal", is_overhead=True,
                      reversal_of_id=original.id)
        result = self.summary()
        self.assertEqual(result["rows"][0]["title"], "Genel gider")
        self.assertTrue(result["rows"][0]["incoming"])
        self.assertEqual(result["rows"][0]["amount"], 100)

    def test_finance_snapshot_keeps_balances_and_cross_month_corrections(self):
        previous = self.movement(1000, direction="in", kind="sale",
            occurred_at=istanbul_to_utc(datetime(2026, 9, 30, 23)))
        self.movement(1000, kind="reversal", reversal_of_id=previous.id)
        self.movement(500, direction="in", kind="sale")
        self.movement(25, kind="return")
        self.movement(20, is_overhead=True)
        commission = self.movement(10, kind="pos_commission")
        self.movement(10, direction="in", kind="reversal", reversal_of_id=commission.id)
        self.movement(999, direction="in", site_id=2)
        self.movement(888, direction="in", store_id=2)
        result = build_finance_snapshot(site_id=1, store_ids=[1], selected_month=date(2026, 10, 1))
        self.assertEqual(result["consolidated_balance"], 455)
        self.assertEqual(result["gross_revenue"], -500)
        self.assertEqual(result["net_revenue"], -525)
        self.assertEqual(result["actual_overhead"], 20)
        self.assertEqual(result["pos_commission_expense"], 0)

    def test_finance_snapshot_does_not_materialize_historical_movements(self):
        for _ in range(30):
            self.movement(100, occurred_at=istanbul_to_utc(datetime(2025, 1, 1)))
        db.session.commit()
        db.session.expunge_all()
        loaded = []
        def record(instance, context):
            loaded.append(instance.id)
        event.listen(FinanceMovement, "load", record)
        try:
            result = build_finance_snapshot(site_id=1, store_ids=[1], selected_month=date(2026, 10, 1))
        finally:
            event.remove(FinanceMovement, "load", record)
        self.assertEqual(result["consolidated_balance"], -3000)
        self.assertEqual(result["net_revenue"], 0)
        self.assertEqual(loaded, [])

    def test_dashboard_hidden_without_ledger_permission(self):
        with patch("app.modules.dashboard.routes.has_permission", side_effect=lambda p: p != "finance.ledger.view"), patch("app.modules.dashboard.routes.build_lobby_finance") as build:
            response = self.app.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        build.assert_not_called()
        self.assertNotIn("Bu Ayın Finans Özeti", response.get_data(as_text=True))

    def test_dashboard_empty_and_escaped_description(self):
        client = self.app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Bu Ayın Finans Özeti", response.get_data(as_text=True))
        self.assertIn("Bu ay henüz finans hareketi kaydedilmedi", response.get_data(as_text=True))
        self.movement(description="<script>alert(1)</script>", occurred_at=datetime.utcnow())
        response = client.get("/")
        self.assertNotIn("<script>alert(1)</script>", response.get_data(as_text=True))
