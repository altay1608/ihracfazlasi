import importlib
import unittest


class PackageScopeTests(unittest.TestCase):
    def test_package_scope_ladder_matches_commercial_definition(self):
        migration = importlib.import_module(
            "migrations.versions.f3a4b5c6d7e8_refine_package_feature_scopes"
        )

        basic = set(migration.BASIC_FEATURES)
        standard = set(migration.STANDARD_FEATURES)
        pro = set(migration.PRO_FEATURES)

        self.assertLess(basic, standard)
        self.assertLess(standard, pro)
        self.assertTrue({"products", "sales", "inventory_history"}.issubset(basic))
        self.assertTrue({"alerts", "inventory_counts"}.issubset(standard - basic))
        self.assertEqual({"profit_reports", "audit", "identity"}, pro - standard)
        self.assertNotIn("platform", pro)


if __name__ == "__main__":
    unittest.main()
