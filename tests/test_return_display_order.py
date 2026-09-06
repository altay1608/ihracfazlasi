import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader


class ReturnDisplayOrderTests(unittest.TestCase):
    def test_exchange_summary_lists_returned_item_before_replacement(self):
        template_root = Path(__file__).resolve().parents[1] / "app" / "templates"
        environment = Environment(loader=FileSystemLoader(template_root), autoescape=True)
        environment.globals["url_for"] = lambda *args, **kwargs: "/returns/"
        environment.globals["can"] = lambda _permission: True
        environment.filters["tr_date"] = lambda value: "19.08.2026"
        product = lambda name: SimpleNamespace(name=name, variant=None)
        record = SimpleNamespace(
            id=1,
            document_no=1,
            original_sale_id=70,
            original_sale=SimpleNamespace(document_no=70),
            return_date=None,
            type="degisim",
            status="tamamlandi",
            reason="Test",
            note=None,
            items=[
                SimpleNamespace(product=product("Yeni Urun"), quantity=1, refund_amount=Decimal("-50.00")),
                SimpleNamespace(product=product("Iade Urun"), quantity=1, refund_amount=Decimal("100.00")),
            ],
        )

        html = environment.get_template("returns/_list_section.html").render(
            return_records=[record],
            return_types={"degisim": "Değişim"},
        )

        self.assertLess(html.index("İade: Iade Urun"), html.index("Yeni Ürün: Yeni Urun"))


if __name__ == "__main__":
    unittest.main()
