import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import (
    AuditLog,
    Category,
    FinanceAccount,
    FinanceCategory,
    FinanceMovement,
    FinancePaymentMapping,
    InventoryCount,
    InventoryCountLine,
    InventoryTransaction,
    Package,
    PosReconciliation,
    Product,
    ProductBarcode,
    RetailMultiplier,
    Sale,
    SaleItem,
    Site,
    SiteDocumentSequence,
    Store,
    StoreInventory,
    SystemSetting,
)
from app.services.deployment_bootstrap import (
    DELIVERY_RESET_VERSION,
    reset_customer_delivery_data_once,
)
from app.services.finance import activate_finance, sync_sale_finance
from app.services.inventory_history import record_inventory_movement
from app.services.product_inventory import (
    MIN_PRODUCT_CODE,
    get_next_product_code,
    sync_product_barcodes,
)
from config import BaseConfig


class CustomerDeliveryResetTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parent / f"_delivery_reset_{uuid4().hex}.db"
        self.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.database_path.as_posix()}"
        self.app = create_app("development")
        self.app.config.update(TESTING=True, AUTH_ENABLED=False)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        package = Package(code="PRO", name="Pro")
        self.site = Site(code="IFG", name="İhraç Fazlası Giyim", package=package)
        self.store = Store(code="MERKEZ", name="Merkez", site=self.site)
        db.session.add_all([package, self.site, self.store])
        db.session.flush()
        category = Category(name="Tişört", site_id=self.site.id)
        multiplier = RetailMultiplier(
            name="Standart",
            multiplier=Decimal("1.8000"),
            site_id=self.site.id,
            is_default=True,
        )
        db.session.add_all([category, multiplier])
        db.session.commit()
        self.multiplier = multiplier

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()
        BaseConfig.SQLALCHEMY_DATABASE_URI = self.old_database_uri
        self.database_path.unlink(missing_ok=True)

    def test_reset_clears_operational_data_but_keeps_customer_setup(self):
        product = Product(
            site_id=self.site.id,
            name="Teslimat Test Ürünü",
            category="Tişört",
            barcode=str(MIN_PRODUCT_CODE),
            product_code=str(MIN_PRODUCT_CODE),
            purchase_price=Decimal("100.00"),
            sale_price=Decimal("180.00"),
            stock_quantity=1,
            variant="S",
            retail_multiplier_id=self.multiplier.id,
        )
        db.session.add(product)
        db.session.flush()
        sync_product_barcodes(product, 1)
        record_inventory_movement(
            product,
            transaction_type="product_opening",
            quantity_before=0,
            quantity_after=1,
            source_type="test",
            source_id=product.id,
        )
        count = InventoryCount(
            site_id=self.site.id,
            store_id=self.store.id,
            name="Deneme Sayımı",
        )
        db.session.add(count)
        db.session.flush()
        db.session.add(
            InventoryCountLine(
                site_id=self.site.id,
                store_id=self.store.id,
                inventory_count_id=count.id,
                product_id=product.id,
                system_quantity=1,
                counted_quantity=1,
                unit_cost=Decimal("100.00"),
            )
        )
        sale = Sale(
            site_id=self.site.id,
            store_id=self.store.id,
            sale_date=datetime.utcnow(),
            total_amount=Decimal("198.00"),
            payment_method="Kredi Kartı",
        )
        sale.items.append(
            SaleItem(
                site_id=self.site.id,
                store_id=self.store.id,
                product=product,
                quantity=1,
                delivered_quantity=1,
                unit_price=Decimal("180.00"),
            )
        )
        db.session.add(sale)
        activate_finance(self.site.id, self.store.id)
        db.session.flush()
        sync_sale_finance(sale)
        db.session.add(
            AuditLog(
                site_id=self.site.id,
                store_id=self.store.id,
                event_type="test",
                action="delivery_seed",
            )
        )
        db.session.add(
            FinanceAccount(
                site_id=self.site.id,
                store_id=self.store.id,
                code="TEST",
                display_code="99",
                name="Deneme Hesabı",
                account_type="bank",
                is_system=False,
            )
        )
        db.session.add(
            FinanceCategory(
                site_id=self.site.id,
                code="TEST",
                name="Deneme Kategorisi",
                direction="out",
                is_system=False,
            )
        )
        db.session.commit()

        self.assertTrue(reset_customer_delivery_data_once(self.site.id))

        self.assertEqual(Product.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(ProductBarcode.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(StoreInventory.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(InventoryTransaction.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(InventoryCount.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(Sale.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(SaleItem.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(FinanceMovement.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(PosReconciliation.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(AuditLog.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(SiteDocumentSequence.query.filter_by(site_id=self.site.id).count(), 0)
        self.assertEqual(
            FinanceAccount.query.filter_by(site_id=self.site.id, is_system=False).count(), 0
        )
        self.assertEqual(
            FinanceCategory.query.filter_by(site_id=self.site.id, is_system=False).count(), 0
        )
        self.assertEqual(
            FinancePaymentMapping.query.filter_by(site_id=self.site.id).count(), 4
        )
        self.assertEqual(get_next_product_code(self.site.id), str(MIN_PRODUCT_CODE))
        self.assertIsNotNone(db.session.get(Site, self.site.id))
        self.assertIsNotNone(Category.query.filter_by(site_id=self.site.id, name="Tişört").one_or_none())
        marker = db.session.get(SystemSetting, f"{DELIVERY_RESET_VERSION}:{self.site.id}")
        self.assertEqual(marker.value, "completed")
        self.assertFalse(reset_customer_delivery_data_once(self.site.id))


if __name__ == "__main__":
    unittest.main()
