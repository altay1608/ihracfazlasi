import unittest
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from flask import session

from app import create_app
from app.extensions import db
from app.models import InventoryCount, Package, Product, ProductBarcode, Return, Sale, SaleItem, Site, Store
from app.services.product_inventory import sync_product_barcodes
from config import BaseConfig


class TenantScopeTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parent / f"_tenant_scope_{uuid4().hex}.db"
        self.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.database_path.as_posix()}"
        self.app = None
        self.addCleanup(self._cleanup)

        self.app = create_app("development")
        self.app.config.update(TESTING=True, AUTH_ENABLED=False)
        with self.app.app_context():
            db.create_all()
            package = Package(code="PRO-TEST", name="Pro Test")
            lfa = Site(code="LFA-TEST", name="LFA Test", package=package, is_sandbox=False)
            dev = Site(code="DEV-TEST", name="DEV Test", package=package, is_sandbox=True)
            lfa_store = Store(code="MERKEZ", name="Merkez", site=lfa)
            dev_store = Store(code="TEST", name="Test", site=dev)
            db.session.add_all([package, lfa, dev, lfa_store, dev_store])
            db.session.commit()
            self.lfa_site_id = lfa.id
            self.dev_site_id = dev.id
            self.lfa_store_id = lfa_store.id
            self.dev_store_id = dev_store.id

            self._seed_product_and_sale(self.lfa_site_id, self.lfa_store_id, "LFA Ürün")
            self._seed_product_and_sale(self.dev_site_id, self.dev_store_id, "DEV Ürün")

    def _cleanup(self):
        if self.app is not None:
            with self.app.app_context():
                db.session.remove()
                db.drop_all()
                db.engine.dispose()
        BaseConfig.SQLALCHEMY_DATABASE_URI = self.old_database_uri
        self.database_path.unlink(missing_ok=True)

    def _request_context(self, site_id, store_id):
        context = self.app.test_request_context("/")
        context.push()
        session["auth_user"] = "tenant-test"
        session["active_site_id"] = site_id
        session["active_store_id"] = store_id
        return context

    def _seed_product_and_sale(self, site_id, store_id, product_name):
        context = self._request_context(site_id, store_id)
        try:
            product = Product(
                site_id=site_id,
                name=product_name,
                category="Test",
                barcode="SHARED-0001",
                product_code="SHARED-0001",
                purchase_price=Decimal("100.00"),
                sale_price=Decimal("200.00"),
                stock_quantity=2,
            )
            sale = Sale(
                site_id=site_id,
                store_id=store_id,
                total_amount=Decimal("200.00"),
                payment_method="Nakit",
            )
            sale.items.append(
                SaleItem(
                    site_id=site_id,
                    store_id=store_id,
                    product=product,
                    quantity=1,
                    unit_price=Decimal("200.00"),
                )
            )
            db.session.add(sale)
            db.session.flush()
            sync_product_barcodes(product, 2)
            db.session.commit()
        finally:
            context.pop()

    def test_site_and_store_queries_are_isolated_including_line_tables(self):
        with self.app.app_context():
            lfa_context = self._request_context(self.lfa_site_id, self.lfa_store_id)
            try:
                self.assertEqual([item.name for item in Product.query.all()], ["LFA Ürün"])
                self.assertEqual(Sale.query.count(), 1)
                self.assertEqual(SaleItem.query.count(), 1)
                self.assertEqual(
                    [item.barcode for item in ProductBarcode.query.order_by(ProductBarcode.sequence_no).all()],
                    ["SHARED-0001-01", "SHARED-0001-02"],
                )
            finally:
                lfa_context.pop()

            dev_context = self._request_context(self.dev_site_id, self.dev_store_id)
            try:
                self.assertEqual([item.name for item in Product.query.all()], ["DEV Ürün"])
                self.assertEqual(Sale.query.count(), 1)
                self.assertEqual(SaleItem.query.count(), 1)
                self.assertEqual(
                    [item.barcode for item in ProductBarcode.query.order_by(ProductBarcode.sequence_no).all()],
                    ["SHARED-0001-01", "SHARED-0001-02"],
                )
            finally:
                dev_context.pop()

    def test_cross_site_write_is_rejected(self):
        with self.app.app_context():
            context = self._request_context(self.dev_site_id, self.dev_store_id)
            try:
                db.session.add(
                    Product(
                        site_id=self.lfa_site_id,
                        name="Yanlış Kapsam",
                        category="Test",
                        barcode="WRONG-SCOPE",
                        product_code="WRONG-SCOPE",
                        purchase_price=Decimal("1.00"),
                        sale_price=Decimal("2.00"),
                        stock_quantity=1,
                    )
                )
                with self.assertRaises(ValueError):
                    db.session.flush()
                db.session.rollback()
            finally:
                context.pop()

    def test_product_without_inventory_in_active_store_does_not_show_legacy_stock(self):
        with self.app.app_context():
            empty_store = Store(site_id=self.dev_site_id, code="EMPTY", name="Boş Mağaza")
            db.session.add(empty_store)
            db.session.commit()
            empty_store_id = empty_store.id

            context = self._request_context(self.dev_site_id, empty_store_id)
            try:
                product = Product.query.filter_by(name="DEV Ürün").one()
                self.assertEqual(product.stock_quantity, 0)
                self.assertEqual(ProductBarcode.query.count(), 0)
            finally:
                context.pop()

    def test_site_document_numbers_restart_per_site_and_advance_independently(self):
        with self.app.app_context():
            lfa_context = self._request_context(self.lfa_site_id, self.lfa_store_id)
            try:
                lfa_first_sale = Sale.query.one()
                self.assertEqual(lfa_first_sale.document_no, 1)
                lfa_second_sale = Sale(
                    site_id=self.lfa_site_id,
                    store_id=self.lfa_store_id,
                    total_amount=Decimal("10.00"),
                    payment_method="Nakit",
                )
                lfa_return = Return(
                    site_id=self.lfa_site_id,
                    store_id=self.lfa_store_id,
                    original_sale_id=lfa_first_sale.id,
                    reason="Test",
                    type="iade",
                )
                lfa_count = InventoryCount(
                    site_id=self.lfa_site_id,
                    store_id=self.lfa_store_id,
                    name="LFA Sayim",
                )
                db.session.add_all([lfa_second_sale, lfa_return, lfa_count])
                db.session.commit()
                self.assertEqual(lfa_second_sale.document_no, 2)
                self.assertEqual(lfa_return.document_no, 1)
                self.assertEqual(lfa_count.document_no, 1)
            finally:
                lfa_context.pop()

            dev_context = self._request_context(self.dev_site_id, self.dev_store_id)
            try:
                dev_first_sale = Sale.query.one()
                self.assertEqual(dev_first_sale.document_no, 1)
                dev_second_sale = Sale(
                    site_id=self.dev_site_id,
                    store_id=self.dev_store_id,
                    total_amount=Decimal("10.00"),
                    payment_method="Nakit",
                )
                dev_return = Return(
                    site_id=self.dev_site_id,
                    store_id=self.dev_store_id,
                    original_sale_id=dev_first_sale.id,
                    reason="Test",
                    type="iade",
                )
                dev_count = InventoryCount(
                    site_id=self.dev_site_id,
                    store_id=self.dev_store_id,
                    name="DEV Sayim",
                )
                db.session.add_all([dev_second_sale, dev_return, dev_count])
                db.session.commit()
                self.assertEqual(dev_second_sale.document_no, 2)
                self.assertEqual(dev_return.document_no, 1)
                self.assertEqual(dev_count.document_no, 1)
            finally:
                dev_context.pop()


if __name__ == "__main__":
    unittest.main()
