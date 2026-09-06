import unittest
from types import SimpleNamespace

from app.security_catalog import (
    CUSTOMER_REPRESENTATIVE_PERMISSIONS,
    FEATURES,
    PERMISSIONS,
    validate_security_catalog,
)
from app.services.identity_access import (
    IdentityScopeError,
    eligible_operational_memberships,
    is_operational_site_allowed,
    validate_membership_scope,
)


def record(**values):
    return SimpleNamespace(**values)


class IdentityFoundationTests(unittest.TestCase):
    def test_security_catalog_is_valid_and_complete(self):
        validate_security_catalog()

        self.assertEqual(len(FEATURES), 14)
        self.assertEqual(len(PERMISSIONS), 64)

    def test_customer_representative_defaults_allow_returns_without_sensitive_finance(self):
        self.assertIn("returns.action.create", CUSTOMER_REPRESENTATIVE_PERMISSIONS)
        self.assertIn("dashboard.column.sales_trend", CUSTOMER_REPRESENTATIVE_PERMISSIONS)
        self.assertNotIn("dashboard.column.finance", CUSTOMER_REPRESENTATIVE_PERMISSIONS)
        self.assertNotIn("products.column.purchase_price", CUSTOMER_REPRESENTATIVE_PERMISSIONS)
        self.assertNotIn("products.action.multiplier", CUSTOMER_REPRESENTATIVE_PERMISSIONS)
        self.assertNotIn("profit_reports.access", CUSTOMER_REPRESENTATIVE_PERMISSIONS)

    def test_platform_superadmin_can_operate_only_in_sandbox(self):
        platform_user = record(is_active=True, is_platform_superadmin=True)
        lfa_site = record(is_active=True, is_sandbox=False)
        dev_site = record(is_active=True, is_sandbox=True)

        self.assertFalse(is_operational_site_allowed(platform_user, lfa_site))
        self.assertTrue(is_operational_site_allowed(platform_user, dev_site))
        with self.assertRaises(IdentityScopeError):
            validate_membership_scope(platform_user, lfa_site)

    def test_platform_membership_list_excludes_customer_sites(self):
        active_role = record(is_active=True)
        platform_user = record(is_active=True, is_platform_superadmin=True)
        lfa_membership = record(
            is_active=True,
            role=active_role,
            site=record(is_active=True, is_sandbox=False),
        )
        dev_membership = record(
            is_active=True,
            role=active_role,
            site=record(is_active=True, is_sandbox=True),
        )
        platform_user.memberships = [lfa_membership, dev_membership]

        self.assertEqual(eligible_operational_memberships(platform_user), (dev_membership,))

    def test_site_user_can_operate_only_through_active_memberships(self):
        active_role = record(is_active=True)
        site_user = record(is_active=True, is_platform_superadmin=False)
        membership = record(
            is_active=True,
            role=active_role,
            site=record(is_active=True, is_sandbox=False),
        )
        site_user.memberships = [membership]

        self.assertEqual(eligible_operational_memberships(site_user), (membership,))


if __name__ == "__main__":
    unittest.main()
