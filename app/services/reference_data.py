from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.models import Category, PaymentMethod, RetailMultiplier, ReturnReason, Variant


DEFAULT_CATEGORIES = [
    ("Tişört", "Basic, polo ve baskılı tişörtler"),
    ("Gömlek", "Klasik, günlük ve oversize erkek gömlekleri"),
    ("Sweatshirt", "Kapüşonlu ve bisiklet yaka sweatshirtler"),
    ("Kazak", "Triko ve örgü erkek kazakları"),
    ("Hırka", "Düğmeli ve fermuarlı erkek hırkaları"),
    ("Ceket", "Blazer, spor ve günlük erkek ceketleri"),
    ("Mont ve Kaban", "Mevsimlik mont, parka ve kabanlar"),
    ("Pantolon", "Kumaş, chino ve günlük pantolonlar"),
    ("Jean", "Erkek jean ve denim pantolonlar"),
    ("Eşofman", "Alt ve üst eşofman grupları"),
    ("Şort", "Günlük, spor ve deniz şortları"),
    ("Takım Elbise", "Takım elbise, smokin ve kombinler"),
    ("Yelek", "Klasik, şişme ve spor yelekler"),
    ("İç Giyim", "Atlet, boxer ve iç giyim ürünleri"),
    ("Ayakkabı", "Klasik, spor ve günlük ayakkabılar"),
    ("Aksesuar", "Kemer, kravat, çorap, çanta ve aksesuarlar"),
    ("Diğer", "Sistem fallback kategorisi"),
]

DEFAULT_VARIANTS = [
    "S", "M", "L", "XL", "XXL", "3XL", "4XL",
    "30", "31", "32", "33", "34", "36", "38", "40", "42",
]
DEFAULT_PAYMENT_METHODS = [
    ("Nakit", True),
    ("Kredi Kartı", True),
    ("Havale/EFT", True),
    ("Veresiye", True),
]
DEFAULT_RETURN_REASONS = [
    "Beden Uyumsuzluğu",
    "Ürün Hasarlı",
    "Beğenilmedi",
    "Renk Farkı",
    "Diğer",
]
DEFAULT_RETAIL_MULTIPLIERS = [
    ("Standart 1.80x", 1.80, True),
    ("Premium 2.00x", 2.00, False),
    ("Luxury 2.25x", 2.25, False),
]


def ensure_reference_data():
    try:
        changed = False

        if Category.query.count() == 0:
            for name, description in DEFAULT_CATEGORIES:
                db.session.add(Category(name=name, description=description, is_active=True))
                changed = True

        existing_variants = {item.name: item for item in Variant.query.all()}
        for name in DEFAULT_VARIANTS:
            variant = existing_variants.get(name)
            if variant is None:
                db.session.add(Variant(name=name, is_active=True))
                changed = True
            elif not variant.is_active:
                variant.is_active = True
                changed = True
        for name, variant in existing_variants.items():
            if name not in DEFAULT_VARIANTS and variant.is_active:
                variant.is_active = False
                changed = True

        supported_payment_methods = {name: is_active for name, is_active in DEFAULT_PAYMENT_METHODS}
        existing_payment_methods = {item.name: item for item in PaymentMethod.query.all()}
        for name, is_active in DEFAULT_PAYMENT_METHODS:
            method = existing_payment_methods.get(name)
            if method is None:
                db.session.add(PaymentMethod(name=name, is_active=is_active))
                changed = True
            elif method.is_active != is_active:
                method.is_active = is_active
                changed = True
        for name, method in existing_payment_methods.items():
            if name not in supported_payment_methods and method.is_active:
                method.is_active = False
                changed = True

        if ReturnReason.query.count() == 0:
            for name in DEFAULT_RETURN_REASONS:
                db.session.add(ReturnReason(name=name, is_active=True))
                changed = True

        if RetailMultiplier.query.count() == 0:
            default_exists = False
            for name, multiplier, is_default in DEFAULT_RETAIL_MULTIPLIERS:
                db.session.add(
                    RetailMultiplier(
                        name=name,
                        multiplier=multiplier,
                        is_active=True,
                        is_default=is_default and not default_exists,
                    )
                )
                changed = True
                default_exists = default_exists or is_default
        elif not RetailMultiplier.query.filter_by(is_default=True).first():
            first_multiplier = RetailMultiplier.query.order_by(RetailMultiplier.id.asc()).first()
            if first_multiplier:
                first_multiplier.is_default = True
                changed = True

        if changed:
            db.session.commit()
    except OperationalError:
        db.session.rollback()


def get_category_choices(include_blank=False):
    ensure_reference_data()
    choices = [(item.name, item.name) for item in Category.query.order_by(Category.name.asc()).all()]
    if include_blank:
        return [("", "Seçiniz")] + choices
    return choices


def get_variant_choices(include_blank=True):
    ensure_reference_data()
    choices = [
        (item.name, item.name)
        for item in Variant.query.filter_by(is_active=True).order_by(Variant.name.asc()).all()
    ]
    if include_blank:
        return [("", "Varyant Yok")] + choices
    return choices


def get_payment_method_choices(active_only=True):
    ensure_reference_data()
    query = PaymentMethod.query
    if active_only:
        query = query.filter_by(is_active=True)
    return [(item.name, item.name) for item in query.order_by(PaymentMethod.name.asc()).all()]


def get_payment_method_map(active_only=False):
    return dict(get_payment_method_choices(active_only=active_only))


def get_return_reason_choices():
    ensure_reference_data()
    return [(item.name, item.name) for item in ReturnReason.query.order_by(ReturnReason.name.asc()).all()]


def get_retail_multiplier_choices(include_blank=False):
    ensure_reference_data()
    choices = [
        (str(item.id), f"{item.name} ({float(item.multiplier):.2f}x)")
        for item in RetailMultiplier.query.order_by(RetailMultiplier.multiplier.asc(), RetailMultiplier.name.asc()).all()
    ]
    if include_blank:
        return [("", "Seçiniz")] + choices
    return choices


def get_default_retail_multiplier():
    ensure_reference_data()
    return (
        RetailMultiplier.query.filter_by(is_default=True).order_by(RetailMultiplier.id.asc()).first()
        or RetailMultiplier.query.order_by(RetailMultiplier.multiplier.asc(), RetailMultiplier.id.asc()).first()
    )
