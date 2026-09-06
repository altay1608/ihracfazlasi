import unittest
from decimal import Decimal
from types import SimpleNamespace

from werkzeug.datastructures import MultiDict

from app.modules.returns.routes import (
    build_return_receipt_context,
    calculate_line_refund_allocations,
    collect_line_inputs,
    validate_unit_barcode_selections,
)


class ReturnReceiptTests(unittest.TestCase):
    def test_return_receipt_displays_refund_with_vat(self):
        return_record = SimpleNamespace(
            type="iade",
            items=[
                SimpleNamespace(
                    refund_amount=Decimal("477.27"),
                    quantity=1,
                    product=SimpleNamespace(name="Test Urun", variant=None),
                )
            ],
        )

        receipt = build_return_receipt_context(return_record)

        self.assertEqual(receipt["line_items"][0]["refund_amount"], Decimal("525.00"))
        self.assertEqual(receipt["total_refund"], Decimal("525.00"))
        self.assertEqual(receipt["vat_rate"], 10)

    def test_exchange_receipt_displays_both_sides_with_vat(self):
        return_record = SimpleNamespace(
            type="degisim",
            items=[
                SimpleNamespace(
                    refund_amount=Decimal("100.00"),
                    quantity=1,
                    product=SimpleNamespace(name="Iade Urun", variant=None),
                ),
                SimpleNamespace(
                    refund_amount=Decimal("-50.00"),
                    quantity=1,
                    product=SimpleNamespace(name="Yeni Urun", variant=None),
                ),
            ],
        )

        receipt = build_return_receipt_context(return_record)

        self.assertEqual(receipt["line_items"][0]["refund_amount"], Decimal("110.00"))
        self.assertEqual(receipt["line_items"][0]["type"], "Iade")
        self.assertEqual(receipt["line_items"][1]["refund_amount"], Decimal("-55.00"))
        self.assertEqual(receipt["line_items"][1]["type"], "Yeni Urun")
        self.assertEqual(receipt["total_refund"], Decimal("55.00"))

    def test_unit_barcode_form_creates_one_row_per_selected_unit(self):
        form_data = MultiDict(
            [
                ("return_barcode_10_101", "990000000001-01"),
                ("replacement_barcode_10_101", "990000000002-01"),
                ("return_barcode_11_102", "990000000003-01"),
                ("replacement_barcode_11_102", "990000000004-01"),
            ]
        )

        rows = collect_line_inputs(form_data)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["quantity"], 1)
        self.assertEqual(rows[0]["barcode_values"], ["990000000001-01"])
        self.assertEqual(rows[0]["replacement_product_lookup"], "990000000002-01")
        self.assertEqual(rows[1]["sale_item_id"], 11)

    def test_duplicate_return_or_replacement_barcode_is_rejected(self):
        duplicate_return_rows = [
            {
                "sale_item_id": 10,
                "quantity": 1,
                "barcode_values": ["990000000001-01"],
                "replacement_product_lookup": "",
            },
            {
                "sale_item_id": 10,
                "quantity": 1,
                "barcode_values": ["990000000001-01"],
                "replacement_product_lookup": "",
            },
        ]
        with self.assertRaisesRegex(ValueError, "birden fazla"):
            validate_unit_barcode_selections(duplicate_return_rows, "iade")

        duplicate_replacement_rows = [
            {
                "sale_item_id": 10,
                "quantity": 1,
                "barcode_values": ["990000000001-01"],
                "replacement_product_lookup": "990000000003-01",
            },
            {
                "sale_item_id": 10,
                "quantity": 1,
                "barcode_values": ["990000000001-02"],
                "replacement_product_lookup": "990000000003-01",
            },
        ]
        with self.assertRaisesRegex(ValueError, "birden fazla"):
            validate_unit_barcode_selections(duplicate_replacement_rows, "degisim")

    def test_split_unit_refunds_preserve_aggregate_discount_total(self):
        product = SimpleNamespace(name="Test Urun")
        sale_item = SimpleNamespace(
            id=10,
            product=product,
            product_id=1,
            quantity=3,
            unit_price=Decimal("10.00"),
            discount_amount=Decimal("0.00"),
        )
        sale = SimpleNamespace(items=[sale_item], total_discount=Decimal("1.00"))
        rows = [
            {"sale_item_id": 10, "quantity": 1},
            {"sale_item_id": 10, "quantity": 1},
        ]

        allocations = calculate_line_refund_allocations(sale, {10: sale_item}, rows)

        self.assertEqual(allocations[0], Decimal("9.67"))
        self.assertEqual(allocations[1], Decimal("9.66"))
        self.assertEqual(sum(allocations.values()), Decimal("19.33"))

    def test_split_receipt_units_keep_previous_aggregate_rounding(self):
        product = SimpleNamespace(id=1, name="Test Urun", variant=None)
        sale_item = SimpleNamespace(
            id=10,
            product=product,
            product_id=1,
            quantity=3,
            unit_price=Decimal("10.00"),
            discount_amount=Decimal("0.00"),
        )
        sale = SimpleNamespace(items=[sale_item], total_discount=Decimal("1.00"))
        return_record = SimpleNamespace(
            type="iade",
            original_sale=sale,
            items=[
                SimpleNamespace(product=product, product_id=1, quantity=1, refund_amount=Decimal("9.67")),
                SimpleNamespace(product=product, product_id=1, quantity=1, refund_amount=Decimal("9.66")),
            ],
        )

        receipt = build_return_receipt_context(return_record)

        self.assertEqual(receipt["total_refund"], Decimal("20.00"))
        self.assertEqual(
            sum((item["refund_amount"] for item in receipt["line_items"]), Decimal("0.00")),
            Decimal("20.00"),
        )


if __name__ == "__main__":
    unittest.main()
