import unittest
from pathlib import Path


class FrontendGuardTests(unittest.TestCase):
    def test_product_selection_sync_ignores_non_product_tables(self):
        source = (Path(__file__).resolve().parents[1] / "app/static/js/main.js").read_text(encoding="utf-8")
        function_start = source.index("function syncProductSelectionState(section)")
        guard_start = source.index("if (!section)", function_start)
        query_start = source.index("section.querySelectorAll", function_start)

        self.assertLess(guard_start, query_start)


if __name__ == "__main__":
    unittest.main()
