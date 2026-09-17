import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import Product, RetailMultiplier
from config import BaseConfig


class ProductMultiVariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_path = Path(__file__).resolve().parent / f"_product_variants_{uuid4().hex}.db"
        cls.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.database_path.as_posix()}"
        cls.app = create_app("development")
        cls.app.config.update(AUTH_ENABLED=False, TESTING=True, WTF_CSRF_ENABLED=False)
        with cls.app.app_context():
            db.create_all()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        BaseConfig.SQLALCHEMY_DATABASE_URI = cls.old_database_uri
        cls.database_path.unlink(missing_ok=True)

    def test_add_form_creates_each_selected_size_and_opens_one_label_batch(self):
        form_response = self.client.get("/products/add")
        self.assertEqual(form_response.status_code, 200)
        form_html = form_response.get_data(as_text=True)
        self.assertIn('name="variants"', form_html)
        self.assertIn("Üst Giyim Bedenleri", form_html)
        self.assertIn("Alt Giyim Bedenleri", form_html)
        self.assertIn('value="S"', form_html)
        self.assertIn('value="XL"', form_html)
        self.assertIn('value="4XL"', form_html)
        self.assertNotIn('value="28"', form_html)
        self.assertNotIn('value="29"', form_html)
        self.assertNotIn('value="44"', form_html)
        self.assertNotIn('value="60"', form_html)
        self.assertIn('<option selected value="Tişört">Tişört</option>', form_html)

        with self.app.app_context():
            preferred_multiplier = RetailMultiplier.query.filter_by(multiplier=3.25).one()
            self.assertIn(
                f'<option selected value="{preferred_multiplier.id}">Pro 3.25 (3.25x)</option>',
                form_html,
            )

        with self.app.app_context():
            multiplier_id = RetailMultiplier.query.filter_by(is_default=True).one().id

        response = self.client.post(
            "/products/add",
            data={
                "name": "Çok Bedenli Gömlek",
                "category": "Gömlek",
                "product_code": "100000000001",
                "purchase_price": "100.00",
                "retail_multiplier_id": str(multiplier_id),
                "sale_price": "180.00",
                "stock_quantity": "2",
                "variants": ["S", "M", "L", "XL"],
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertTrue(result["success"])
        self.assertIn("4 beden", result["message"])
        product_ids = [int(value) for value in parse_qs(urlparse(result["print_url"]).query)["product_ids"]]

        with self.app.app_context():
            products = Product.query.order_by(Product.product_code.asc()).all()
            self.assertEqual([product.variant for product in products], ["S", "M", "L", "XL"])
            self.assertEqual([product.product_code for product in products], [
                "100000000001", "100000000002", "100000000003", "100000000004",
            ])
            self.assertTrue(all(product.stock_quantity == 2 for product in products))
            self.assertTrue(all(len(product.product_barcodes) == 2 for product in products))
            self.assertEqual(product_ids, [product.id for product in products])

        label_response = self.client.get(result["print_url"])
        label_html = label_response.get_data(as_text=True)
        self.assertEqual(label_response.status_code, 200)
        self.assertEqual(label_html.count('class="label-card compact-fashion-label"'), 8)
        self.assertIn("İHRAÇ FAZLASI GİYİM", label_html)
        self.assertIn("BEDEN", label_html)
        self.assertIn("compact-fashion-label-code", label_html)
        self.assertNotIn("Atelier", label_html)
        self.assertNotIn("₺", label_html)


if __name__ == "__main__":
    unittest.main()
