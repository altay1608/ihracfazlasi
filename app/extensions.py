from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.utils import utc_to_istanbul


db = SQLAlchemy()
migrate = Migrate()


def register_template_filters(app):
    @app.template_filter("currency")
    def currency_filter(value):
        amount = Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"₺{formatted}"

    @app.template_filter("tr_date")
    def tr_date_filter(value):
        if value is None:
            return "-"
        if isinstance(value, datetime):
            return value.strftime("%d.%m.%Y")
        return value.strftime("%d.%m.%Y")

    @app.template_filter("percentage")
    def percentage_filter(value):
        amount = Decimal(value or 0).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        formatted = f"{amount:f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"%{formatted or '0'}"

    @app.template_filter("tr_datetime")
    def tr_datetime_filter(value):
        if value is None:
            return "-"
        if isinstance(value, datetime):
            return utc_to_istanbul(value).strftime("%d.%m.%Y %H:%M")
        return value.strftime("%d.%m.%Y %H:%M")
