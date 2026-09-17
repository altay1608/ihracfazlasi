from flask_wtf import FlaskForm
from wtforms import DecimalField, IntegerField, SelectField, SelectMultipleField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.services.reference_data import (
    get_category_choices,
    get_retail_multiplier_choices,
    get_variant_choices,
)


UPPER_BODY_VARIANTS = ["S", "M", "L", "XL", "XXL", "3XL", "4XL"]
LOWER_BODY_VARIANTS = ["30", "31", "32", "33", "34", "36", "38", "40", "42"]
VARIANT_DISPLAY_ORDER = UPPER_BODY_VARIANTS + LOWER_BODY_VARIANTS


def sort_variant_choices(choices):
    order = {name: index for index, name in enumerate(VARIANT_DISPLAY_ORDER)}
    return sorted(choices, key=lambda item: (order.get(item[0], len(order)), item[1]))


class ProductForm(FlaskForm):
    name = StringField("Ürün Adı", validators=[DataRequired(), Length(max=150)])
    category = SelectField("Kategori", validators=[DataRequired()], choices=[])
    product_code = StringField("Ürün Kodu", validators=[DataRequired(), Length(max=32)])
    purchase_price = DecimalField(
        "Alış Fiyatı",
        places=2,
        rounding=None,
        validators=[DataRequired(), NumberRange(min=0)],
    )
    retail_multiplier_id = SelectField("Perakende Çarpanı", validators=[DataRequired()], choices=[])
    sale_price = DecimalField(
        "Satış Fiyatı",
        places=2,
        rounding=None,
        validators=[DataRequired(), NumberRange(min=0)],
    )
    stock_quantity = IntegerField("Stok", default=1, validators=[DataRequired(), NumberRange(min=0)])
    critical_stock_level = IntegerField("Ürün Bazlı KSS", validators=[Optional(), NumberRange(min=0)])
    barcode_mode = SelectField(
        "Barkod Tipi",
        default="unit",
        choices=[
            ("unit", "Her adet için ayrı barkod (kıyafet)"),
            ("shared", "Tek ortak barkod (parfüm/aksesuar)"),
        ],
        validators=[DataRequired()],
    )
    variant = SelectField("Beden / Varyant", validators=[Optional()], choices=[])
    variants = SelectMultipleField("Eklenecek Bedenler", validators=[Optional()], choices=[])
    submit = SubmitField("Kaydet")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category.choices = get_category_choices()
        variant_choices = sort_variant_choices(get_variant_choices(include_blank=False))
        self.variant.choices = [("", "Varyant Yok")] + variant_choices
        self.variants.choices = [("__none__", "Varyant Yok")] + variant_choices
        self.upper_body_variants = UPPER_BODY_VARIANTS
        self.lower_body_variants = LOWER_BODY_VARIANTS
        self.retail_multiplier_id.choices = get_retail_multiplier_choices()
