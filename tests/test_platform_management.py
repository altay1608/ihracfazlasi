import re
import unittest
from pathlib import Path
from uuid import uuid4

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Feature, Package, PaymentMethod, Permission, Role, Site, Store, User, UserSiteRole
from app.security_catalog import FEATURES, PERMISSIONS
from config import BaseConfig


class PlatformManagementTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parent / f"_platform_{uuid4().hex}.db"
        self.old_database_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        BaseConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.database_path.as_posix()}"
        self.app = create_app("development")
        self.app.config.update(TESTING=True, AUTH_ENABLED=True)

        with self.app.app_context():
            db.create_all()
            feature_by_code = {}
            for code, name, sort_order in FEATURES:
                feature = Feature(code=code, name=name, sort_order=sort_order)
                db.session.add(feature)
                feature_by_code[code] = feature
            db.session.flush()

            permission_by_code = {}
            for code, name, kind, parent_code, feature_code, sort_order in PERMISSIONS:
                permission = Permission(
                    code=code,
                    name=name,
                    kind=kind,
                    parent=permission_by_code.get(parent_code),
                    feature=feature_by_code[feature_code],
                    sort_order=sort_order,
                )
                db.session.add(permission)
                permission_by_code[code] = permission

            package = Package(
                code="PRO",
                name="Pro",
                max_stores=10,
                max_users=25,
                features=list(feature_by_code.values()),
            )
            dev = Site(code="DEV", name="Development Sandbox", package=package, is_sandbox=True)
            lfa = Site(code="LFA", name="La Femme Atelier", package=package, is_sandbox=False)
            dev_store = Store(code="TEST", name="Test Mağaza", site=dev)
            lfa_store = Store(code="MERKEZ", name="Merkez Mağaza", site=lfa)
            dev_owner = Role(code="OWNER_MANAGER", name="Mağaza Yöneticisi / Sahip", site=dev)
            lfa_owner = Role(code="OWNER_MANAGER", name="Mağaza Yöneticisi / Sahip", site=lfa)
            lfa_rep = Role(code="CUSTOMER_REPRESENTATIVE", name="Mağaza Müşteri Temsilcisi", site=lfa)
            dev_owner.permissions = list(permission_by_code.values())
            lfa_owner.permissions = [
                item for item in permission_by_code.values() if not item.code.startswith("platform.")
            ]
            lfa_rep.permissions = [
                permission_by_code["dashboard.access"],
                permission_by_code["dashboard.column.stock"],
                permission_by_code["dashboard.column.sales_trend"],
                permission_by_code["products.access"],
                permission_by_code["products.column.sale_vat"],
                permission_by_code["products.column.stock"],
            ]
            admin = User(
                username="admin",
                full_name="Platform Admin",
                password_hash=generate_password_hash("AdminSecret123"),
                must_change_password=False,
                is_platform_superadmin=True,
            )
            representative = User(
                username="temsilci",
                full_name="Mağaza Temsilcisi",
                password_hash=generate_password_hash("Temsilci123"),
                must_change_password=False,
            )
            db.session.add_all(
                [package, dev, lfa, dev_store, lfa_store, dev_owner, lfa_owner, lfa_rep, admin, representative]
            )
            db.session.flush()
            db.session.add_all(
                [
                    UserSiteRole(
                        user_id=admin.id,
                        site_id=dev.id,
                        role_id=dev_owner.id,
                        all_stores=True,
                    ),
                    UserSiteRole(
                        user_id=representative.id,
                        site_id=lfa.id,
                        role_id=lfa_rep.id,
                        all_stores=True,
                    ),
                ]
            )
            db.session.commit()
            self.package_id = package.id
            self.dev_id = dev.id
            self.dev_store_id = dev_store.id
            self.dev_role_id = dev_owner.id
            self.lfa_id = lfa.id
            self.lfa_store_id = lfa_store.id
            self.lfa_owner_role_id = lfa_owner.id
            self.lfa_rep_role_id = lfa_rep.id
            self.representative_id = representative.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        BaseConfig.SQLALCHEMY_DATABASE_URI = self.old_database_uri
        self.database_path.unlink(missing_ok=True)

    def _csrf(self, client, path="/login"):
        response = client.get(path)
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def _login(self, client, username, password):
        return client.post(
            "/login",
            data={
                "username": username,
                "password": password,
                "csrf_token": self._csrf(client),
                "next": "/",
            },
            follow_redirects=False,
        )

    def test_permission_matrix_is_platform_admin_only(self):
        admin_client = self.app.test_client()
        self.assertEqual(self._login(admin_client, "admin", "AdminSecret123").status_code, 302)
        platform_page = admin_client.get(f"/platform/sites/{self.lfa_id}")
        self.assertEqual(platform_page.status_code, 200)
        platform_html = platform_page.get_data(as_text=True)
        self.assertIn("Rol ve yetki matrisi", platform_html)
        self.assertEqual(platform_html.count("data-role-selector="), 2)
        self.assertIn("data-permission-menu-toggle", platform_html)
        self.assertIn('aria-expanded="false"', platform_html)
        self.assertIn("permission-switch-track", platform_html)
        self.assertIn("Platform Yönetimine Dön", platform_html)
        self.assertNotIn('data-modal-title="Yeni Ürün Ekle"', platform_html)
        self.assertNotIn(">Satış Ekranı</a>", platform_html)

        rep_client = self.app.test_client()
        self.assertEqual(self._login(rep_client, "temsilci", "Temsilci123").status_code, 302)
        denied = rep_client.get(f"/platform/sites/{self.lfa_id}")
        self.assertEqual(denied.status_code, 403)
        products = rep_client.get("/products/")
        html = products.get_data(as_text=True)
        self.assertEqual(products.status_code, 200)
        self.assertNotIn("Platform Yönetimi", html)
        self.assertNotIn("Rol ve yetki matrisi", html)
        dashboard = rep_client.get("/").get_data(as_text=True)
        self.assertNotIn("Ciro Kilidi", dashboard)
        self.assertNotIn("tahmini kâr", dashboard)

    def test_hidden_action_is_also_blocked_by_direct_url(self):
        client = self.app.test_client()
        self.assertEqual(self._login(client, "temsilci", "Temsilci123").status_code, 302)
        products = client.get("/products/")
        self.assertEqual(products.status_code, 200)
        self.assertNotIn("Yeni Ürün Ekle", products.get_data(as_text=True))
        self.assertEqual(client.get("/products/add").status_code, 403)

    def test_platform_admin_can_adjust_owner_permissions(self):
        client = self.app.test_client()
        self.assertEqual(self._login(client, "admin", "AdminSecret123").status_code, 302)
        response = client.post(
            f"/platform/sites/{self.lfa_id}/roles/{self.lfa_owner_role_id}/permissions",
            data={
                "csrf_token": self._csrf(client, f"/platform/sites/{self.lfa_id}"),
                "permission_codes": ["dashboard.column.stock"],
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            role = db.session.get(Role, self.lfa_owner_role_id)
            self.assertEqual(
                {permission.code for permission in role.permissions},
                {"dashboard.access", "dashboard.column.stock"},
            )

    def test_inactive_user_with_correct_password_gets_distinct_message(self):
        with self.app.app_context():
            representative = User.query.filter_by(username="temsilci").one()
            representative.is_active = False
            db.session.commit()

        correct_client = self.app.test_client()
        response = self._login(correct_client, "temsilci", "Temsilci123")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Kullanıcı hesabınız pasif durumdadır", response.get_data(as_text=True))

        wrong_client = self.app.test_client()
        wrong_response = self._login(wrong_client, "temsilci", "YanlisParola123")
        self.assertEqual(wrong_response.status_code, 200)
        wrong_html = wrong_response.get_data(as_text=True)
        self.assertIn("Kullanıcı adı veya şifre hatalı", wrong_html)
        self.assertNotIn("pasif durumdadır", wrong_html)

    def test_platform_admin_can_create_scoped_site_with_first_store_and_roles(self):
        client = self.app.test_client()
        self.assertEqual(self._login(client, "admin", "AdminSecret123").status_code, 302)
        response = client.post(
            "/platform/sites/new",
            data={
                "csrf_token": self._csrf(client, "/platform/sites/new"),
                "site_name": "FY Butik",
                "site_code": "FYB",
                "package_id": str(self.package_id),
                "store_name": "Merkez Mağaza",
                "store_code": "MERKEZ",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            site = Site.query.filter_by(code="FYB").one()
            self.assertFalse(site.is_sandbox)
            self.assertEqual(site.package_id, self.package_id)
            self.assertEqual([(store.code, store.name) for store in site.stores], [("MERKEZ", "Merkez Mağaza")])
            roles = {role.code: role for role in site.roles}
            self.assertEqual(set(roles), {"OWNER_MANAGER", "CUSTOMER_REPRESENTATIVE"})
            owner_codes = {permission.code for permission in roles["OWNER_MANAGER"].permissions}
            representative_codes = {
                permission.code for permission in roles["CUSTOMER_REPRESENTATIVE"].permissions
            }
            self.assertIn("products.action.edit", owner_codes)
            self.assertNotIn("platform.access", owner_codes)
            self.assertIn("products.action.label", representative_codes)
            self.assertNotIn("products.action.edit", representative_codes)
            self.assertGreater(PaymentMethod.query.filter_by(site_id=site.id).count(), 0)

    def test_site_creation_rejects_package_without_feature_scope(self):
        with self.app.app_context():
            package = Package(code="BASIC", name="Baz", is_active=True)
            db.session.add(package)
            db.session.commit()
            empty_package_id = package.id

        client = self.app.test_client()
        self.assertEqual(self._login(client, "admin", "AdminSecret123").status_code, 302)
        response = client.post(
            "/platform/sites/new",
            data={
                "csrf_token": self._csrf(client, "/platform/sites/new"),
                "site_name": "Eksik Paket Sitesi",
                "site_code": "EPS",
                "package_id": str(empty_package_id),
                "store_name": "Merkez Mağaza",
                "store_code": "MERKEZ",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("paketin kapsamı henüz tanımlanmadı", response.get_data(as_text=True))
        with self.app.app_context():
            self.assertIsNone(Site.query.filter_by(code="EPS").first())

    def test_platform_admin_can_add_and_manage_additional_store(self):
        client = self.app.test_client()
        self.assertEqual(self._login(client, "admin", "AdminSecret123").status_code, 302)

        last_store_response = client.post(
            f"/platform/sites/{self.lfa_id}/stores/{self.lfa_store_id}/edit",
            data={
                "csrf_token": self._csrf(
                    client,
                    f"/platform/sites/{self.lfa_id}/stores/{self.lfa_store_id}/edit",
                ),
                "name": "Merkez Mağaza",
                "code": "MERKEZ",
            },
            follow_redirects=True,
        )
        self.assertEqual(last_store_response.status_code, 200)
        self.assertIn("son aktif mağazası pasife alınamaz", last_store_response.get_data(as_text=True))

        create_response = client.post(
            f"/platform/sites/{self.lfa_id}/stores/new",
            data={
                "csrf_token": self._csrf(client, f"/platform/sites/{self.lfa_id}/stores/new"),
                "name": "Cadde Mağazası",
                "code": "CADDE",
                "is_active": "1",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 302)

        with self.app.app_context():
            cadde = Store.query.filter_by(site_id=self.lfa_id, code="CADDE").one()
            cadde_id = cadde.id
            self.assertTrue(cadde.is_active)

        deactivate_response = client.post(
            f"/platform/sites/{self.lfa_id}/stores/{self.lfa_store_id}/edit",
            data={
                "csrf_token": self._csrf(
                    client,
                    f"/platform/sites/{self.lfa_id}/stores/{self.lfa_store_id}/edit",
                ),
                "name": "Merkez Mağaza",
                "code": "MERKEZ",
            },
            follow_redirects=False,
        )
        self.assertEqual(deactivate_response.status_code, 302)
        with self.app.app_context():
            self.assertFalse(db.session.get(Store, self.lfa_store_id).is_active)
            self.assertTrue(db.session.get(Store, cadde_id).is_active)

        rep_client = self.app.test_client()
        self.assertEqual(self._login(rep_client, "temsilci", "Temsilci123").status_code, 302)
        self.assertEqual(rep_client.get(f"/platform/sites/{self.lfa_id}/stores/new").status_code, 403)

    def test_package_limits_block_extra_active_store_and_user(self):
        with self.app.app_context():
            site = db.session.get(Site, self.lfa_id)
            site.package.max_stores = 1
            site.package.max_users = 1
            db.session.commit()

        client = self.app.test_client()
        self.assertEqual(self._login(client, "admin", "AdminSecret123").status_code, 302)
        store_path = f"/platform/sites/{self.lfa_id}/stores/new"
        store_response = client.post(
            store_path,
            data={
                "csrf_token": self._csrf(client, store_path),
                "name": "İkinci Mağaza",
                "code": "IKINCI",
                "is_active": "1",
            },
            follow_redirects=True,
        )
        self.assertIn("en fazla 1 aktif mağaza", store_response.get_data(as_text=True))

        user_path = f"/platform/sites/{self.lfa_id}/users/new"
        user_response = client.post(
            user_path,
            data={
                "csrf_token": self._csrf(client, user_path),
                "username": "ikinci.kullanici",
                "full_name": "İkinci Kullanıcı",
                "email": "ikinci@example.test",
                "temporary_password": "Temporary123",
                "confirm_password": "Temporary123",
                "role_id": str(self.lfa_rep_role_id),
                "all_stores": "1",
                "is_active": "1",
            },
            follow_redirects=True,
        )
        self.assertIn("en fazla 1 aktif kullanıcı", user_response.get_data(as_text=True))

        with self.app.app_context():
            self.assertIsNone(Store.query.filter_by(site_id=self.lfa_id, code="IKINCI").first())
            self.assertIsNone(User.query.filter_by(username="ikinci.kullanici").first())

    def test_site_package_change_enforces_limits_and_preserves_role_preferences(self):
        with self.app.app_context():
            dashboard = Feature.query.filter_by(code="dashboard").one()
            products = Feature.query.filter_by(code="products").one()
            profit_permission = Permission.query.filter_by(code="profit_reports.access").one()
            representative_role = db.session.get(Role, self.lfa_rep_role_id)
            representative_role.permissions.append(profit_permission)
            basic = Package(
                code="BASIC",
                name="Baz",
                max_stores=1,
                max_users=2,
                features=[dashboard, products],
            )
            extra_store = Store(
                site_id=self.lfa_id,
                code="CADDE",
                name="Cadde Mağazası",
                is_active=True,
            )
            db.session.add_all([basic, extra_store])
            db.session.commit()
            basic_id = basic.id
            extra_store_id = extra_store.id

        client = self.app.test_client()
        self.assertEqual(self._login(client, "admin", "AdminSecret123").status_code, 302)
        path = f"/platform/sites/{self.lfa_id}/package"
        blocked = client.post(
            path,
            data={"csrf_token": self._csrf(client, f"/platform/sites/{self.lfa_id}"), "package_id": basic_id},
            follow_redirects=True,
        )
        self.assertIn("en fazla 1 aktif mağazaya izin verir", blocked.get_data(as_text=True))
        with self.app.app_context():
            self.assertEqual(db.session.get(Site, self.lfa_id).package_id, self.package_id)
            db.session.get(Store, extra_store_id).is_active = False
            db.session.commit()

        changed = client.post(
            path,
            data={"csrf_token": self._csrf(client, f"/platform/sites/{self.lfa_id}"), "package_id": basic_id},
            follow_redirects=True,
        )
        html = changed.get_data(as_text=True)
        self.assertIn("Baz paketine geçirildi", html)
        self.assertIn("Aktif mağaza", html)
        self.assertIn("1 / 1", html)
        self.assertIn("Paket dışında", html)
        self.assertIn("kayıtlı rol tercihleri paket yeniden yükseltildiğinde", html)
        self.assertRegex(
            html,
            r'value="profit_reports\.access"[^>]*checked[^>]*disabled',
        )
        with self.app.app_context():
            site = db.session.get(Site, self.lfa_id)
            owner = db.session.get(Role, self.lfa_owner_role_id)
            representative = db.session.get(Role, self.lfa_rep_role_id)
            self.assertEqual(site.package_id, basic_id)
            self.assertIn("products.action.edit", {item.code for item in owner.permissions})
            self.assertIn("profit_reports.access", {item.code for item in owner.permissions})
            self.assertIn("profit_reports.access", {item.code for item in representative.permissions})

        representative_client = self.app.test_client()
        self.assertEqual(self._login(representative_client, "temsilci", "Temsilci123").status_code, 302)
        self.assertEqual(representative_client.get("/reports/profit").status_code, 403)
        basic_products_html = representative_client.get("/products/").get_data(as_text=True)
        self.assertNotIn("Karlılık Analizi", basic_products_html)
        self.assertNotIn("Kritik Stok", basic_products_html)
        self.assertIn('data-stock-palette-enabled="0"', basic_products_html)
        self.assertNotIn("stock-status-low", basic_products_html)
        self.assertNotIn("stock-status-critical", basic_products_html)

        rejected = client.post(
            f"/platform/sites/{self.lfa_id}/roles/{self.lfa_rep_role_id}/permissions",
            data={
                "csrf_token": self._csrf(client, f"/platform/sites/{self.lfa_id}"),
                "permission_codes": ["products.access", "profit_reports.access"],
            },
            follow_redirects=True,
        )
        self.assertIn("Paket dışında veya geçersiz bir yetki seçildi", rejected.get_data(as_text=True))

        restored = client.post(
            path,
            data={
                "csrf_token": self._csrf(client, f"/platform/sites/{self.lfa_id}"),
                "package_id": self.package_id,
            },
            follow_redirects=True,
        )
        self.assertIn("Pro paketine geçirildi", restored.get_data(as_text=True))
        self.assertEqual(representative_client.get("/reports/profit").status_code, 302)
        self.assertEqual(self._login(representative_client, "temsilci", "Temsilci123").status_code, 302)
        self.assertEqual(representative_client.get("/reports/profit").status_code, 200)
        restored_products_html = representative_client.get("/products/").get_data(as_text=True)
        self.assertIn("Karlılık Analizi", restored_products_html)

    def test_standard_package_keeps_stock_controls_and_reserves_pro_features(self):
        with self.app.app_context():
            standard_feature_codes = {
                "dashboard",
                "products",
                "inventory_history",
                "sales",
                "daily_reports",
                "returns",
                "reference_data",
                "alerts",
                "inventory_counts",
            }
            standard = Package(
                code="STANDARD",
                name="Orta",
                max_stores=3,
                max_users=8,
                features=Feature.query.filter(Feature.code.in_(standard_feature_codes)).all(),
            )
            representative_role = db.session.get(Role, self.lfa_rep_role_id)
            for permission_code in (
                "inventory_counts.access",
                "profit_reports.access",
                "audit.access",
                "identity.access",
            ):
                permission = Permission.query.filter_by(code=permission_code).one()
                if permission not in representative_role.permissions:
                    representative_role.permissions.append(permission)
            db.session.add(standard)
            db.session.commit()
            standard_id = standard.id

        admin_client = self.app.test_client()
        self.assertEqual(self._login(admin_client, "admin", "AdminSecret123").status_code, 302)
        site_path = f"/platform/sites/{self.lfa_id}"
        changed = admin_client.post(
            f"{site_path}/package",
            data={"csrf_token": self._csrf(admin_client, site_path), "package_id": standard_id},
            follow_redirects=True,
        )
        html = changed.get_data(as_text=True)
        self.assertIn("Orta paketine geçirildi", html)

        count_input = re.search(r'<input[^>]*value="inventory_counts\.access"[^>]*>', html)
        profit_input = re.search(r'<input[^>]*value="profit_reports\.access"[^>]*>', html)
        audit_input = re.search(r'<input[^>]*value="audit\.access"[^>]*>', html)
        identity_input = re.search(r'<input[^>]*value="identity\.access"[^>]*>', html)
        self.assertIsNotNone(count_input)
        self.assertNotIn("disabled", count_input.group(0))
        for pro_input in (profit_input, audit_input, identity_input):
            self.assertIsNotNone(pro_input)
            self.assertIn("disabled", pro_input.group(0))

        representative_client = self.app.test_client()
        self.assertEqual(self._login(representative_client, "temsilci", "Temsilci123").status_code, 302)
        self.assertEqual(representative_client.get("/inventory-counts/").status_code, 200)
        self.assertEqual(representative_client.get("/reports/profit").status_code, 403)
        self.assertEqual(representative_client.get("/audit-logs/").status_code, 403)

        restored = admin_client.post(
            f"{site_path}/package",
            data={"csrf_token": self._csrf(admin_client, site_path), "package_id": self.package_id},
            follow_redirects=True,
        )
        self.assertIn("Pro paketine geçirildi", restored.get_data(as_text=True))
        self.assertEqual(representative_client.get("/reports/profit").status_code, 302)
        self.assertEqual(self._login(representative_client, "temsilci", "Temsilci123").status_code, 302)
        self.assertEqual(representative_client.get("/reports/profit").status_code, 200)
        self.assertEqual(representative_client.get("/audit-logs/").status_code, 200)

    def test_user_update_message_uses_username(self):
        client = self.app.test_client()
        self.assertEqual(self._login(client, "admin", "AdminSecret123").status_code, 302)
        edit_path = f"/platform/sites/{self.lfa_id}/users/{self.representative_id}/edit"
        response = client.post(
            edit_path,
            data={
                "csrf_token": self._csrf(client, edit_path),
                "username": "lfa.testtemsilci",
                "full_name": "İsmail Çaşka DENEME2",
                "email": "",
                "temporary_password": "",
                "confirm_password": "",
                "role_id": str(self.lfa_rep_role_id),
                "all_stores": "1",
                "is_active": "1",
            },
            follow_redirects=True,
        )
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("lfa.testtemsilci kullanıcısı güncellendi", html)
        self.assertNotIn("İsmail Çaşka DENEME2 kullanıcısı güncellendi", html)

    def test_platform_admin_can_reset_user_two_factor_enrollment(self):
        with self.app.app_context():
            representative = db.session.get(User, self.representative_id)
            representative.two_factor_secret = "encrypted-test-secret"
            representative.two_factor_enabled = True
            representative.two_factor_recovery_codes = "[]"
            representative.two_factor_last_counter = 42
            db.session.commit()

        client = self.app.test_client()
        self.assertEqual(self._login(client, "admin", "AdminSecret123").status_code, 302)
        edit_path = f"/platform/sites/{self.lfa_id}/users/{self.representative_id}/edit"
        page = client.get(edit_path)
        self.assertIn("İki adımlı doğrulamayı sıfırla", page.get_data(as_text=True))
        response = client.post(
            edit_path,
            data={
                "csrf_token": self._csrf(client, edit_path),
                "username": "temsilci",
                "full_name": "Mağaza Temsilcisi",
                "email": "",
                "temporary_password": "",
                "confirm_password": "",
                "role_id": str(self.lfa_rep_role_id),
                "all_stores": "1",
                "is_active": "1",
                "reset_two_factor": "1",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            representative = db.session.get(User, self.representative_id)
            self.assertFalse(representative.two_factor_enabled)
            self.assertIsNone(representative.two_factor_secret)
            self.assertIsNone(representative.two_factor_recovery_codes)
            self.assertIsNone(representative.two_factor_last_counter)

        reset_page = client.get(edit_path)
        reset_html = reset_page.get_data(as_text=True)
        self.assertIn("İki Adımlı Doğrulama", reset_html)
        self.assertIn("Kurulum bekliyor", reset_html)
        self.assertIn("sıfırlanacak bir iki adımlı doğrulama kaydı bulunmuyor", reset_html)
        self.assertNotIn('name="reset_two_factor"', reset_html)

    def test_management_pages_hide_quick_actions_and_forms_have_contextual_back_links(self):
        client = self.app.test_client()
        self.assertEqual(self._login(client, "admin", "AdminSecret123").status_code, 302)

        management_paths = (
            "/account",
            "/platform/",
            f"/platform/sites/{self.lfa_id}",
            "/audit-logs/",
            "/admin/",
        )
        for path in management_paths:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertNotIn('data-modal-title="Yeni Ürün Ekle"', html)
                self.assertNotIn(">Satış Ekranı</a>", html)

        user_form = client.get(f"/platform/sites/{self.lfa_id}/users/{self.representative_id}/edit")
        user_html = user_form.get_data(as_text=True)
        self.assertEqual(user_form.status_code, 200)
        self.assertIn("Site Yönetimine Dön", user_html)
        self.assertIn(">Vazgeç</a>", user_html)

        store_form = client.get(f"/platform/sites/{self.lfa_id}/stores/new")
        store_html = store_form.get_data(as_text=True)
        self.assertEqual(store_form.status_code, 200)
        self.assertIn("Site Yönetimine Dön", store_html)
        self.assertIn(">Vazgeç</a>", store_html)

    def test_login_uses_first_authorized_page_when_dashboard_is_disabled(self):
        with self.app.app_context():
            representative = User.query.filter_by(username="temsilci").one()
            membership = UserSiteRole.query.filter_by(user_id=representative.id).one()
            membership.role.permissions = [
                permission
                for permission in membership.role.permissions
                if permission.code != "dashboard.access" and not permission.code.startswith("dashboard.column.")
            ]
            db.session.commit()

        client = self.app.test_client()
        response = self._login(client, "temsilci", "Temsilci123")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/products/"))

    def test_platform_created_user_must_change_temporary_password(self):
        admin_client = self.app.test_client()
        self.assertEqual(self._login(admin_client, "admin", "AdminSecret123").status_code, 302)
        form_page = admin_client.get(f"/platform/sites/{self.lfa_id}/users/new")
        self.assertEqual(form_page.status_code, 200)
        create_response = admin_client.post(
            f"/platform/sites/{self.lfa_id}/users/new",
            data={
                "csrf_token": self._csrf(admin_client, f"/platform/sites/{self.lfa_id}/users/new"),
                "username": "lfa.sahip",
                "full_name": "LFA Mağaza Sahibi",
                "email": "sahip@example.test",
                "temporary_password": "Temporary123",
                "confirm_password": "Temporary123",
                "role_id": str(self.lfa_owner_role_id),
                "all_stores": "1",
                "is_active": "1",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 302)

        with self.app.app_context():
            created = User.query.filter_by(username="lfa.sahip").one()
            membership = UserSiteRole.query.filter_by(user_id=created.id).one()
            self.assertTrue(created.must_change_password)
            self.assertFalse(created.is_platform_superadmin)
            self.assertEqual(membership.site_id, self.lfa_id)

        user_client = self.app.test_client()
        login_response = self._login(user_client, "lfa.sahip", "Temporary123")
        self.assertEqual(login_response.status_code, 302)
        self.assertTrue(login_response.headers["Location"].endswith("/account"))
        forced = user_client.get("/products/", follow_redirects=False)
        self.assertEqual(forced.status_code, 302)
        self.assertTrue(forced.headers["Location"].endswith("/account"))

        account_page = user_client.get("/account")
        account_html = account_page.get_data(as_text=True)
        self.assertNotIn(">Yeni Ürün<", account_html)
        self.assertNotIn(">Satış Ekranı<", account_html)

        account_token = self._csrf(user_client, "/account")
        changed = user_client.post(
            "/account",
            data={
                "csrf_token": account_token,
                "current_password": "Temporary123",
                "new_password": "Permanent123",
                "confirm_password": "Permanent123",
            },
            follow_redirects=False,
        )
        self.assertEqual(changed.status_code, 302)
        self.assertEqual(user_client.get("/products/").status_code, 200)
        self.assertEqual(user_client.get("/platform/").status_code, 403)


if __name__ == "__main__":
    unittest.main()
