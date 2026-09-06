"""Canonical feature and permission definitions for package and role enforcement."""

FEATURES = (
    ("dashboard", "Kontrol Merkezi", 10),
    ("products", "Ürün ve Stok", 20),
    ("inventory_history", "Envanter İşlem Tarihçesi", 30),
    ("sales", "Satış İşlemleri", 40),
    ("daily_reports", "Günlük Rapor", 50),
    ("profit_reports", "Karlılık Analizi", 60),
    ("returns", "İade ve Değişim", 70),
    ("alerts", "Kritik Stok Uyarıları", 80),
    ("inventory_counts", "Stok Sayım Yönetimi", 90),
    ("reference_data", "Temel Veri Yönetimi", 100),
    ("audit", "Sistem Günlüğü", 110),
    ("identity", "Kullanıcı ve Yetki Yönetimi", 120),
    ("platform", "Platform Yönetimi", 130),
    ("finance_management", "Finans Yönetimi ve Ön Muhasebe", 140),
)


PERMISSIONS = (
    ("dashboard.access", "Kontrol merkezini görüntüle", "menu", None, "dashboard", 10),
    ("dashboard.column.finance", "Ciro, indirim ve kâr göstergelerini görüntüle", "column", "dashboard.access", "dashboard", 11),
    ("dashboard.column.stock", "Stok sağlık göstergelerini görüntüle", "column", "dashboard.access", "dashboard", 12),
    ("dashboard.column.sales_trend", "Satış performansı ve ürün trendlerini görüntüle", "column", "dashboard.access", "dashboard", 13),
    ("products.access", "Ürün ve stok ekranını görüntüle", "menu", None, "products", 20),
    ("products.column.purchase_price", "Alış fiyatını görüntüle", "column", "products.access", "products", 21),
    ("products.column.purchase_vat", "KDV dahil alış fiyatını görüntüle", "column", "products.access", "products", 22),
    ("products.column.sale_net", "KDV hariç satış fiyatını görüntüle", "column", "products.access", "products", 23),
    ("products.column.sale_vat", "KDV dahil satış fiyatını görüntüle", "column", "products.access", "products", 24),
    ("products.column.stock", "Stok miktarını görüntüle", "column", "products.access", "products", 25),
    ("products.action.create", "Ürün oluştur", "action", "products.access", "products", 26),
    ("products.action.edit", "Ürün düzenle", "action", "products.access", "products", 27),
    ("products.action.delete", "Ürün sil", "action", "products.access", "products", 28),
    ("products.action.import", "Excel ile ürün yükle", "action", "products.access", "products", 29),
    ("products.action.export", "Ürünleri Excel'e aktar", "action", "products.access", "products", 30),
    ("products.action.label", "Etiket yazdır", "action", "products.access", "products", 31),
    ("products.action.multiplier", "Perakende çarpanı değiştir", "action", "products.access", "products", 32),
    ("products.action.stock", "Stok miktarını elle değiştir", "action", "products.access", "products", 33),
    ("inventory_history.access", "Envanter işlem tarihçesini görüntüle", "menu", None, "inventory_history", 40),
    ("inventory_history.column.cost", "Envanter hareket maliyetini görüntüle", "column", "inventory_history.access", "inventory_history", 41),
    ("sales.access", "Satış sipariş satırlarını görüntüle", "menu", None, "sales", 50),
    ("sales.action.complete", "Yeni satış tamamla", "action", "sales.access", "sales", 51),
    ("sales.action.edit", "Satış siparişini yeniden düzenle", "action", "sales.access", "sales", 52),
    ("sales.action.receipt", "Satış fişi görüntüle ve yazdır", "action", "sales.access", "sales", 53),
    ("sales.customer.view", "Müşteri bilgilerini görüntüle", "column", "sales.access", "sales", 54),
    ("daily_reports.access", "Günlük satış raporunu görüntüle", "menu", None, "daily_reports", 60),
    ("profit_reports.access", "Karlılık analizini görüntüle", "menu", None, "profit_reports", 70),
    ("profit_reports.action.export", "Karlılık analizini Excel'e aktar", "action", "profit_reports.access", "profit_reports", 71),
    ("returns.access", "İade ve değişim kayıtlarını görüntüle", "menu", None, "returns", 80),
    ("returns.action.create", "İade ve değişim oluştur", "action", "returns.access", "returns", 81),
    ("returns.action.receipt", "İade ve değişim fişi yazdır", "action", "returns.access", "returns", 82),
    ("alerts.access", "Kritik stok uyarılarını görüntüle", "menu", None, "alerts", 90),
    ("alerts.action.manage", "Kritik stok eşiklerini değiştir", "action", "alerts.access", "alerts", 91),
    ("inventory_counts.access", "Stok sayımlarını görüntüle", "menu", None, "inventory_counts", 100),
    ("inventory_counts.action.create", "Stok sayımı oluştur", "action", "inventory_counts.access", "inventory_counts", 101),
    ("inventory_counts.action.scan", "Sayım barkodu okut", "action", "inventory_counts.access", "inventory_counts", 102),
    ("inventory_counts.action.save", "Sayım miktarlarını kaydet", "action", "inventory_counts.access", "inventory_counts", 103),
    ("inventory_counts.action.approve", "Sayımı onayla ve stoğa uygula", "action", "inventory_counts.access", "inventory_counts", 104),
    ("inventory_counts.action.delete", "Sayım kaydını sil", "action", "inventory_counts.access", "inventory_counts", 105),
    ("reference_data.access", "Temel veri yönetimini görüntüle", "menu", None, "reference_data", 110),
    ("reference_data.action.manage", "Temel verileri değiştir", "action", "reference_data.access", "reference_data", 111),
    ("audit.access", "Site sistem günlüğünü görüntüle", "menu", None, "audit", 120),
    ("audit.action.manage", "Ekran kayıt tercihlerini değiştir", "action", "audit.access", "audit", 121),
    ("identity.access", "Kullanıcı ve yetki yönetimini görüntüle", "menu", None, "identity", 130),
    ("identity.action.users", "Kullanıcıları yönet", "action", "identity.access", "identity", 131),
    ("identity.action.roles", "Rol ve yetkileri yönet", "action", "identity.access", "identity", 132),
    ("identity.action.stores", "Mağazaları yönet", "action", "identity.access", "identity", 133),
    ("platform.access", "Platform yönetimini görüntüle", "menu", None, "platform", 140),
    ("platform.action.sites", "Siteleri yönet", "action", "platform.access", "platform", 141),
    ("platform.action.packages", "Paketleri yönet", "action", "platform.access", "platform", 142),
    ("platform.action.security_logs", "Platform güvenlik kayıtlarını görüntüle", "action", "platform.access", "platform", 143),
    ("finance.access", "Finans Yönetimini görüntüle", "menu", None, "finance_management", 150),
    ("finance.ledger.view", "Kasa defterini görüntüle", "action", "finance.access", "finance_management", 151),
    ("finance.accounts.view", "Finans hesaplarını görüntüle", "action", "finance.access", "finance_management", 152),
    ("finance.accounts.manage", "Finans hesaplarını yönet", "action", "finance.access", "finance_management", 153),
    ("finance.manual.create", "Manuel finans hareketi oluştur", "action", "finance.access", "finance_management", 154),
    ("finance.transfer.create", "Hesap transferi oluştur", "action", "finance.access", "finance_management", 155),
    ("finance.pos_reconcile.create", "POS mutabakatı oluştur", "action", "finance.access", "finance_management", 156),
    ("finance.current.view", "Cari hesapları görüntüle", "action", "finance.access", "finance_management", 157),
    ("finance.current.manage", "Cari hesapları yönet", "action", "finance.access", "finance_management", 158),
    ("finance.overhead.view", "Genel gider bütçesini görüntüle", "action", "finance.access", "finance_management", 159),
    ("finance.overhead.manage", "Genel gider bütçesini yönet", "action", "finance.access", "finance_management", 160),
    ("finance.obligation.view", "Kısa vadeli borçları görüntüle", "action", "finance.access", "finance_management", 161),
    ("finance.obligation.manage", "Kısa vadeli borçları yönet", "action", "finance.access", "finance_management", 162),
)


CUSTOMER_REPRESENTATIVE_PERMISSIONS = frozenset(
    {
        "dashboard.access",
        "dashboard.column.stock",
        "dashboard.column.sales_trend",
        "products.access",
        "products.column.sale_vat",
        "products.column.stock",
        "products.action.label",
        "sales.access",
        "sales.action.complete",
        "sales.action.receipt",
        "sales.customer.view",
        "returns.access",
        "returns.action.create",
        "returns.action.receipt",
        "alerts.access",
        "inventory_counts.access",
        "inventory_counts.action.create",
        "inventory_counts.action.scan",
        "inventory_counts.action.save",
    }
)


def validate_security_catalog():
    feature_codes = {item[0] for item in FEATURES}
    permission_codes = {item[0] for item in PERMISSIONS}
    if len(feature_codes) != len(FEATURES):
        raise ValueError("Özellik kodları benzersiz olmalıdır.")
    if len(permission_codes) != len(PERMISSIONS):
        raise ValueError("Yetki kodları benzersiz olmalıdır.")
    for code, _name, _kind, parent_code, feature_code, _sort_order in PERMISSIONS:
        if feature_code not in feature_codes:
            raise ValueError(f"{code} için tanımsız özellik: {feature_code}")
        if parent_code and parent_code not in permission_codes:
            raise ValueError(f"{code} için tanımsız üst yetki: {parent_code}")
    if not CUSTOMER_REPRESENTATIVE_PERMISSIONS <= permission_codes:
        raise ValueError("Müşteri temsilcisi rolünde tanımsız yetki bulunuyor.")


validate_security_catalog()
