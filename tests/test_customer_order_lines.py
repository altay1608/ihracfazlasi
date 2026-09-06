import unittest
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from flask import session

from app import create_app
from app.extensions import db
from app.models import Package, Product, ReturnItem, Sale, SaleItem, Site, Store
from app.modules.returns.routes import build_return_record
from app.services.customer_orders import (
    prepare_customer_order,
    refresh_customer_order_return_status,
    register_returned_quantity,
)
from app.services.product_inventory import reserve_barcodes_for_sale, sync_product_barcodes
from config import BaseConfig


class CustomerOrderLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_path = Path(__file__).resolve().parent / f"_customer_orders_{uuid4().hex}.db"
        cls.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.database_path.as_posix()}"
        cls.app = create_app("development")
        cls.app.config.update(TESTING=True, AUTH_ENABLED=False)
        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        BaseConfig.SQLALCHEMY_DATABASE_URI = cls.old_database_uri
        cls.database_path.unlink(missing_ok=True)

    def _create_scope(self):
        suffix = uuid4().hex[:8].upper()
        package = Package(code=f"CO-{suffix}", name="Siparis Test")
        site = Site(code=f"S{suffix}", name="Siparis Test", package=package)
        store = Store(code="MAIN", name="Ana Magaza", site=site)
        db.session.add_all([package, site, store])
        db.session.flush()
        session["active_site_id"] = site.id
        session["active_store_id"] = store.id
        return site, store

    @staticmethod
    def _product(site, code, name, purchase_price, sale_price):
        return Product(
            site_id=site.id,
            name=name,
            category="Test",
            barcode=code,
            product_code=code,
            purchase_price=Decimal(purchase_price),
            sale_price=Decimal(sale_price),
        )

    def test_line_financials_reconcile_exactly_and_freeze_product_context(self):
        with self.app.test_request_context("/"):
            site, store = self._create_scope()
            first_product = self._product(site, "CO000001", "Birinci Urun", "100.00", "9.95")
            second_product = self._product(site, "CO000002", "Ikinci Urun", "200.00", "9.95")
            order = Sale(
                document_no=1,
                site_id=site.id,
                store_id=store.id,
                total_amount=Decimal("20.00"),
                total_discount=Decimal("0.00"),
                payment_method="Nakit",
            )
            order.items.extend(
                [
                    SaleItem(
                        site_id=site.id,
                        store_id=store.id,
                        product=first_product,
                        quantity=1,
                        unit_price=Decimal("9.95"),
                    ),
                    SaleItem(
                        site_id=site.id,
                        store_id=store.id,
                        product=second_product,
                        quantity=1,
                        unit_price=Decimal("9.95"),
                    ),
                ]
            )

            prepare_customer_order(order)
            db.session.add(order)
            db.session.flush()

            self.assertEqual([line.line_no for line in order.items], [1, 2])
            self.assertEqual([line.release_no for line in order.items], [1, 1])
            self.assertEqual(
                [line.gross_amount for line in order.items],
                [Decimal("10.00"), Decimal("10.00")],
            )
            self.assertEqual(
                sum((line.gross_amount for line in order.items), Decimal("0.00")),
                order.total_amount,
            )
            self.assertEqual(order.items[0].product_name_snapshot, "Birinci Urun")
            self.assertEqual(order.items[0].unit_cost_snapshot, Decimal("100.00"))

            first_product.name = "Sonradan Degisen Urun"
            first_product.purchase_price = Decimal("999.00")
            db.session.flush()
            self.assertEqual(order.items[0].product_name_snapshot, "Birinci Urun")
            self.assertEqual(order.items[0].unit_cost_snapshot, Decimal("100.00"))
            db.session.rollback()

    def test_header_discount_is_allocated_without_losing_a_cent(self):
        with self.app.test_request_context("/"):
            site, store = self._create_scope()
            first_product = self._product(site, "CO000003", "Indirimli Urun", "300.00", "1000.00")
            second_product = self._product(site, "CO000004", "Diger Urun", "400.00", "1000.00")
            order = Sale(
                document_no=1,
                site_id=site.id,
                store_id=store.id,
                total_amount=Decimal("2000.00"),
                total_discount=Decimal("181.82"),
                payment_method="Nakit",
            )
            order.items.extend(
                [
                    SaleItem(
                        site_id=site.id,
                        store_id=store.id,
                        product=first_product,
                        quantity=1,
                        unit_price=Decimal("1000.00"),
                        discount_amount=Decimal("50.00"),
                    ),
                    SaleItem(
                        site_id=site.id,
                        store_id=store.id,
                        product=second_product,
                        quantity=1,
                        unit_price=Decimal("1000.00"),
                        discount_amount=Decimal("0.00"),
                    ),
                ]
            )

            prepare_customer_order(order)

            header_discount = sum(
                (line.header_discount_amount for line in order.items),
                Decimal("0.00"),
            )
            gross_total = sum((line.gross_amount for line in order.items), Decimal("0.00"))
            self.assertEqual(header_discount, Decimal("131.82"))
            self.assertEqual(gross_total, Decimal("2000.00"))
            db.session.rollback()

    def test_partial_and_full_returns_advance_line_and_header_statuses(self):
        first_line = SaleItem(quantity=2, delivered_quantity=2, returned_quantity=0)
        second_line = SaleItem(quantity=1, delivered_quantity=1, returned_quantity=0)
        order = Sale(items=[first_line, second_line])

        register_returned_quantity(first_line, 1)
        refresh_customer_order_return_status(order)
        self.assertEqual(first_line.line_status, "PARTIALLY_RETURNED")
        self.assertEqual(order.order_status, "PARTIALLY_RETURNED")
        self.assertEqual(order.payment_status, "PARTIALLY_REFUNDED")

        register_returned_quantity(first_line, 1)
        register_returned_quantity(second_line, 1)
        refresh_customer_order_return_status(order)
        self.assertEqual(first_line.line_status, "RETURNED")
        self.assertEqual(second_line.line_status, "RETURNED")
        self.assertEqual(order.order_status, "RETURNED")
        self.assertEqual(order.payment_status, "REFUNDED")

        with self.assertRaisesRegex(ValueError, "aşamaz"):
            register_returned_quantity(first_line, 1)

    def test_return_record_links_the_returned_unit_to_its_original_order_line(self):
        with self.app.test_request_context("/"):
            site, store = self._create_scope()
            product = self._product(site, "CO000005", "Iade Urunu", "100.00", "200.00")
            db.session.add(product)
            db.session.flush()
            sync_product_barcodes(product, 1)
            db.session.flush()
            unit_barcode = product.product_barcodes[0].barcode

            order = Sale(
                document_no=1,
                site_id=site.id,
                store_id=store.id,
                total_amount=Decimal("220.00"),
                total_discount=Decimal("0.00"),
                payment_method="Nakit",
            )
            order_line = SaleItem(
                site_id=site.id,
                store_id=store.id,
                product=product,
                quantity=1,
                unit_price=Decimal("200.00"),
            )
            order.items.append(order_line)
            prepare_customer_order(order)
            db.session.add(order)
            db.session.flush()
            reserve_barcodes_for_sale(product, order_line, 1, [unit_barcode])
            db.session.flush()

            return_record, _movements = build_return_record(
                order,
                "iade",
                "Test iadesi",
                None,
                [
                    {
                        "sale_item_id": order_line.id,
                        "quantity": 1,
                        "barcode_values": [unit_barcode],
                        "replacement_product_lookup": "",
                    }
                ],
            )
            db.session.add(return_record)
            db.session.flush()

            positive_return = ReturnItem.query.filter_by(
                original_sale_item_id=order_line.id
            ).one()
            self.assertEqual(positive_return.original_sale_item_id, order_line.id)
            self.assertEqual(positive_return.original_sale_item, order_line)
            self.assertEqual(order_line.returned_quantity, 1)
            self.assertEqual(order_line.line_status, "RETURNED")
            self.assertEqual(order.order_status, "RETURNED")
            self.assertEqual(order.payment_status, "REFUNDED")
            self.assertEqual(product.stock_quantity, 1)
            db.session.rollback()

    def test_return_listing_keeps_order_line_product_snapshot_and_reference(self):
        with self.app.test_request_context("/"):
            site, store = self._create_scope()
            product = self._product(site, "CO000007", "Siparis Anindaki Ad", "100.00", "200.00")
            product.variant = "M"
            db.session.add(product)
            db.session.flush()
            sync_product_barcodes(product, 1)
            db.session.flush()
            unit_barcode = product.product_barcodes[0].barcode

            order = Sale(
                document_no=1,
                site_id=site.id,
                store_id=store.id,
                total_amount=Decimal("220.00"),
                total_discount=Decimal("0.00"),
                payment_method="Nakit",
            )
            order_line = SaleItem(
                site_id=site.id,
                store_id=store.id,
                product=product,
                quantity=1,
                unit_price=Decimal("200.00"),
            )
            order.items.append(order_line)
            prepare_customer_order(order)
            db.session.add(order)
            db.session.flush()
            reserve_barcodes_for_sale(product, order_line, 1, [unit_barcode])

            return_record, _movements = build_return_record(
                order,
                "iade",
                "Snapshot testi",
                None,
                [
                    {
                        "sale_item_id": order_line.id,
                        "quantity": 1,
                        "barcode_values": [unit_barcode],
                        "replacement_product_lookup": "",
                    }
                ],
            )
            db.session.add(return_record)
            db.session.flush()
            product.name = "Sonradan Degisen Envanter Adi"
            product.variant = "L"
            db.session.commit()
            site_id = site.id
            store_id = store.id

        client = self.app.test_client()
        with client.session_transaction() as client_session:
            client_session["active_site_id"] = site_id
            client_session["active_store_id"] = store_id

        response = client.get("/returns/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Siparis Anindaki Ad", html)
        self.assertNotIn("Sonradan Degisen Envanter Adi", html)
        self.assertIn("1.1", html)

    def test_returned_order_edit_only_updates_customer_metadata(self):
        with self.app.test_request_context("/"):
            site, store = self._create_scope()
            product = self._product(site, "CO000008", "Korumali Siparis", "100.00", "200.00")
            order = Sale(
                document_no=1,
                site_id=site.id,
                store_id=store.id,
                total_amount=Decimal("220.00"),
                total_discount=Decimal("0.00"),
                payment_method="Nakit",
                customer_name="Eski Musteri",
            )
            order_line = SaleItem(
                site_id=site.id,
                store_id=store.id,
                product=product,
                quantity=1,
                unit_price=Decimal("200.00"),
            )
            order.items.append(order_line)
            prepare_customer_order(order)
            order_line.returned_quantity = 1
            order_line.line_status = "RETURNED"
            order.order_status = "RETURNED"
            db.session.add(order)
            db.session.commit()
            site_id = site.id
            store_id = store.id
            order_id = order.id
            order_line_id = order_line.id

        client = self.app.test_client()
        with client.session_transaction() as client_session:
            client_session["active_site_id"] = site_id
            client_session["active_store_id"] = store_id

        edit_response = client.get(f"/sales/{order_id}/edit")
        update_response = client.post(
            f"/sales/{order_id}/update",
            json={
                "payment_method": "Kredi Kartı",
                "target_final_total": "10.00",
                "items": [],
                "customer": {
                    "customer_name": "Yeni Musteri",
                    "customer_note": "Yalnizca metadata",
                },
            },
        )

        self.assertEqual(edit_response.status_code, 200)
        self.assertIn("lineEditsLocked: true", edit_response.get_data(as_text=True))
        self.assertEqual(update_response.status_code, 200)

        with self.app.app_context():
            preserved_order = db.session.get(Sale, order_id)
            self.assertEqual(preserved_order.customer_name, "Yeni Musteri")
            self.assertEqual(preserved_order.customer_note, "Yalnizca metadata")
            self.assertEqual(preserved_order.payment_method, "Nakit")
            self.assertEqual(preserved_order.total_amount, Decimal("220.00"))
            self.assertEqual(len(preserved_order.items), 1)
            self.assertEqual(preserved_order.items[0].id, order_line_id)
            self.assertEqual(preserved_order.items[0].returned_quantity, 1)

    def test_sales_management_renders_the_order_line_view(self):
        with self.app.test_request_context("/"):
            site, store = self._create_scope()
            product = self._product(site, "CO000006", "Liste Test Urunu", "100.00", "200.00")
            order = Sale(
                document_no=1,
                site_id=site.id,
                store_id=store.id,
                total_amount=Decimal("220.00"),
                total_discount=Decimal("0.00"),
                payment_method="Nakit",
            )
            order.items.append(
                SaleItem(
                    site_id=site.id,
                    store_id=store.id,
                    product=product,
                    quantity=1,
                    unit_price=Decimal("200.00"),
                )
            )
            prepare_customer_order(order)
            db.session.add(order)
            db.session.commit()
            site_id = site.id
            store_id = store.id
            order_id = order.id

        client = self.app.test_client()
        with client.session_transaction() as client_session:
            client_session["active_site_id"] = site_id
            client_session["active_store_id"] = store_id

        list_response = client.get("/sales/")
        detail_response = client.get(f"/sales/{order_id}")
        list_html = list_response.get_data(as_text=True)
        detail_html = detail_response.get_data(as_text=True)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertIn("Satış Sipariş Satırları", list_html)
        self.assertIn("Liste Test Urunu", list_html)
        self.assertIn("Teslim Edildi", list_html)
        self.assertIn("Sipariş #1", detail_html)
        self.assertIn("Satır", detail_html)


if __name__ == "__main__":
    unittest.main()
