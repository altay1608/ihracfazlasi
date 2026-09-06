from flask_wtf import FlaskForm
from wtforms import HiddenField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange

from app.services.reference_data import get_return_reason_choices
from app.utils import RETURN_TYPES


class ReturnForm(FlaskForm):
    original_sale_id = HiddenField(validators=[DataRequired()])
    reason = SelectField("İade / Değişim Nedeni", validators=[DataRequired()], choices=[])
    note = TextAreaField("Açıklama / Not")
    type = SelectField(
        "İşlem Tipi",
        choices=[(key, label) for key, label in RETURN_TYPES.items()],
        validators=[DataRequired()],
    )
    submit = SubmitField("İşlemi Kaydet")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reason.choices = get_return_reason_choices()


class ExchangeLineForm(FlaskForm):
    product_id = HiddenField()
    quantity = IntegerField("Adet", validators=[NumberRange(min=0)], default=0)
    replacement_product_id = StringField("Yeni Ürün ID")
