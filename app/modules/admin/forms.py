from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class CategoryForm(FlaskForm):
    name = StringField("Kategori Adı", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Açıklama", validators=[Optional(), Length(max=500)])
    critical_stock_level = IntegerField("Kategori Bazlı KSS", validators=[Optional(), NumberRange(min=0)])
    is_active = BooleanField("Aktif", default=True)
    submit = SubmitField("Kaydet")


class VariantForm(FlaskForm):
    name = StringField("Beden / Varyant", validators=[DataRequired(), Length(max=50)])
    is_active = BooleanField("Aktif", default=True)
    submit = SubmitField("Kaydet")


class PaymentMethodForm(FlaskForm):
    name = StringField("Ödeme Yöntemi", validators=[DataRequired(), Length(max=120)])
    is_active = BooleanField("Aktif")
    submit = SubmitField("Kaydet")


class ReturnReasonForm(FlaskForm):
    name = StringField("İade Nedeni", validators=[DataRequired(), Length(max=120)])
    is_active = BooleanField("Aktif", default=True)
    submit = SubmitField("Kaydet")


class RetailMultiplierForm(FlaskForm):
    name = StringField("Tanım", validators=[DataRequired(), Length(max=120)])
    multiplier = DecimalField(
        "Çarpan",
        validators=[DataRequired(), NumberRange(min=0.01)],
        places=2,
    )
    is_active = BooleanField("Aktif", default=True)
    is_default = BooleanField("Varsayılan")
    submit = SubmitField("Kaydet")
