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

    def test_telegram_bot_is_limited_to_website_product_uploads(self):
        source = (Path(__file__).resolve().parents[1] / "site/lib/telegram.ts").read_text(encoding="utf-8")
        handler = source[source.index("export async function handleUpdate") :]

        for allowed_command in ('case "/urunekle":', 'case "/foto":', 'case "/fotograflar":'):
            self.assertIn(allowed_command, handler)

        for blocked_command in (
            'case "/sat":',
            'case "/stokdus":',
            'case "/gider":',
            'case "/finans":',
            'case "/kasaac":',
            'case "/defter":',
            'case "/urunsil":',
            'case "/fiyat":',
        ):
            self.assertNotIn(blocked_command, handler)

        self.assertIn("WEBSITE_UPLOAD_STATES", handler)
        self.assertIn("Sesli mağaza komutları kapalıdır", handler)

    def test_telegram_single_quantity_uses_upper_sizes_through_3xl(self):
        source = (Path(__file__).resolve().parents[1] / "site/lib/telegram.ts").read_text(encoding="utf-8")

        self.assertIn('"ust-giyim": ["S", "M", "L", "XL", "XXL", "3XL"]', source)
        self.assertNotIn('"ust-giyim": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"', source)
        self.assertIn("stockUpdates = sizes.map(size => ({ size, quantity }))", source)


if __name__ == "__main__":
    unittest.main()
