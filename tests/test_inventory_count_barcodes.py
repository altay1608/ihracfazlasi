import unittest
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import (
    InventoryCount,
    InventoryCountLine,
    InventoryCountScan,
    InventoryTransaction,
    Package,
    Product,
    ProductBarcode,
    Site,
    Store,
)
from app.services.product_inventory import sync_product_barcodes
from config import BaseConfig


class InventoryCountBarcodeTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parent / f"_count_barcodes_{uuid4().hex}.db"
        self.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.database_path.as_posix()}"
        self.app = create_app("development")
        self.app.config.update(TESTING=True, AUTH_ENABLED=False)
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            package = Package(code="COUNT-TEST", name="Count Test")
            site = Site(code="COUNT", name="Count Site", package=package)
            store = Store(code="MAIN", name="Main Store", site=site)
            db.session.add_all([package, site, store])
            db.session.flush()

            counted_product = Product(
                site_id=site.id,
                name="Sayilan Urun",
                category="Test",
                barcode="COUNT-0001",
                product_code="COUNT-0001",
                purchase_price=Decimal("100.00"),
                sale_price=Decimal("200.00"),
                stock_quantity=3,
            )
            outside_product = Product(
                site_id=site.id,
                name="Liste Disi Urun",
                category="Diger",
                barcode="OUTSIDE-0001",
                product_code="OUTSIDE-0001",
                purchase_price=Decimal("50.00"),
                sale_price=Decimal("100.00"),
                stock_quantity=1,
            )
            db.session.add_all([counted_product, outside_product])
            db.session.flush()
            sync_product_barcodes(counted_product, 3)
            sync_product_barcodes(outside_product, 1)

            inventory_count = InventoryCount(
                site_id=site.id,
                store_id=store.id,
                name="Barkodlu Sayim",
            )
            db.session.add(inventory_count)
            db.session.flush()
            line = InventoryCountLine(
                site_id=site.id,
                store_id=store.id,
                inventory_count=inventory_count,
                product=counted_product,
                system_quantity=3,
                counted_quantity=0,
                unit_cost=Decimal("100.00"),
            )
            db.session.add(line)
            db.session.commit()

            self.count_id = inventory_count.id
            self.count_document_no = inventory_count.document_no
            self.line_id = line.id
            self.product_id = counted_product.id
            self.unit_barcodes = [item.barcode for item in counted_product.product_barcodes]
            self.outside_barcode = outside_product.product_barcodes[0].barcode

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        BaseConfig.SQLALCHEMY_DATABASE_URI = self.old_database_uri
        self.database_path.unlink(missing_ok=True)

    def _scan(self, barcode):
        return self.client.post(
            f"/inventory-counts/{self.count_id}/scan",
            json={"barcode": barcode},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    def test_scan_rejects_unknown_outside_and_duplicate_barcodes(self):
        unknown = self._scan("UNKNOWN-9999")
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.get_json()["error_code"], "barcode_not_found")

        outside = self._scan(self.outside_barcode)
        self.assertEqual(outside.status_code, 400)
        self.assertEqual(outside.get_json()["error_code"], "barcode_not_in_inventory_count")

        first = self._scan(self.unit_barcodes[0])
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["line"]["counted_quantity"], 1)

        duplicate = self._scan(self.unit_barcodes[0])
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.get_json()["error_code"], "barcode_already_counted")

        with self.app.app_context():
            line = db.session.get(InventoryCountLine, self.line_id)
            self.assertEqual(line.counted_quantity, 1)
            self.assertEqual(InventoryCountScan.query.count(), 1)

    def test_scanner_value_without_hyphen_is_rejected(self):
        response = self._scan(self.unit_barcodes[0].replace("-", ""))

        self.assertEqual(response.status_code, 404, response.get_data(as_text=True))
        self.assertEqual(response.get_json()["error_code"], "barcode_not_found")

    def test_counted_quantity_is_read_only_and_reaches_healthy_state_dynamically(self):
        detail = self.client.get(f"/inventory-counts/{self.count_id}")
        html = detail.get_data(as_text=True)
        self.assertEqual(detail.status_code, 200)
        self.assertIn(f"Sayım No:</strong> #{self.count_document_no}", html)
        self.assertNotIn('name="counted_quantity', html)
        self.assertNotIn('type="number"', html)

        responses = [self._scan(barcode) for barcode in self.unit_barcodes]
        self.assertTrue(all(response.status_code == 200 for response in responses))
        last_payload = responses[-1].get_json()
        self.assertEqual(last_payload["line"]["counted_quantity"], 3)
        self.assertEqual(last_payload["line"]["variance_quantity"], 0)

        refreshed = self.client.get(f"/inventory-counts/{self.count_id}").get_data(as_text=True)
        self.assertIn(f'id="count-line-{self.line_id}" class="stock-status-healthy"', refreshed)

    def test_removing_one_exact_scan_controls_approval_and_deleted_unit_barcode(self):
        scan_payloads = [self._scan(barcode).get_json() for barcode in self.unit_barcodes]
        middle_scan = scan_payloads[1]["scan"]

        removed = self.client.post(
            middle_scan["remove_url"],
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.get_json()["line"]["counted_quantity"], 2)

        approved = self.client.post(f"/inventory-counts/{self.count_id}/approve")
        self.assertEqual(approved.status_code, 302)

        with self.app.app_context():
            inventory_count = db.session.get(InventoryCount, self.count_id)
            product = db.session.get(Product, self.product_id)
            remaining = {
                item.barcode
                for item in ProductBarcode.query.filter_by(product_id=self.product_id).all()
            }
            transaction = InventoryTransaction.query.filter_by(
                source_type="inventory_count",
                source_id=self.count_id,
            ).one()

            self.assertEqual(inventory_count.status, "approved")
            self.assertEqual(product.stock_quantity, 2)
            self.assertEqual(remaining, {self.unit_barcodes[0], self.unit_barcodes[2]})
            self.assertNotIn(self.unit_barcodes[1], remaining)
            self.assertEqual(transaction.transaction_code, "COUNT-REM")
            self.assertEqual(transaction.quantity_before, 3)
            self.assertEqual(transaction.quantity_after, 2)
            self.assertEqual(transaction.barcode_values, self.unit_barcodes[1])


if __name__ == "__main__":
    unittest.main()
