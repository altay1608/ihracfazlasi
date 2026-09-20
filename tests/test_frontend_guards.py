import unittest
from pathlib import Path


class FrontendGuardTests(unittest.TestCase):
    def test_product_selection_sync_ignores_non_product_tables(self):
        source = (Path(__file__).resolve().parents[1] / "app/static/js/main.js").read_text(encoding="utf-8")
        function_start = source.index("function syncProductSelectionState(section)")
        guard_start = source.index("if (!section)", function_start)
        query_start = source.index("section.querySelectorAll", function_start)

        self.assertLess(guard_start, query_start)

    def test_pos_escapes_product_fields_before_cart_rendering(self):
        source = (Path(__file__).resolve().parents[1] / "app/static/js/pos.js").read_text(encoding="utf-8")

        self.assertIn("function escapeHtml(value)", source)
        self.assertIn("${escapeHtml(item.name)}", source)
        self.assertIn("${escapeHtml(item.variant || \"\")}", source)
        self.assertNotIn("<strong>${item.name}</strong>", source)

    def test_customer_results_are_created_with_text_content(self):
        source = (Path(__file__).resolve().parents[1] / "app/static/js/pos.js").read_text(encoding="utf-8")

        self.assertIn("function createCustomerButton", source)
        self.assertIn("name.textContent = item.name || fallbackName", source)
        self.assertNotIn("data-customer='${JSON.stringify(item)", source)


if __name__ == "__main__":
    unittest.main()
