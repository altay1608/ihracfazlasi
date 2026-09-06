from flask_wtf import FlaskForm
from wtforms import DecimalField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.services.reference_data import (
    get_category_choices,
    get_retail_multiplier_choices,
    get_variant_choices,
)


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
    stock_quantity = IntegerField("Stok", validators=[DataRequired(), NumberRange(min=0)])
    critical_stock_level = IntegerField("Ürün Bazlı KSS", validators=[Optional(), NumberRange(min=0)])
    variant = SelectField("Beden / Varyant", validators=[Optional()], choices=[])
    submit = SubmitField("Kaydet")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category.choices = get_category_choices()
        self.variant.choices = get_variant_choices()
        self.retail_multiplier_id.choices = get_retail_multiplier_choices()
