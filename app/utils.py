from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import request


PAYMENT_METHODS = {
    "nakit": "Nakit",
    "kredi_karti": "Kredi Kartı",
    "havale": "Havale",
}

RETURN_TYPES = {
    "iade": "İade",
    "degisim": "Değişim",
}


try:
    ISTANBUL_TIMEZONE = ZoneInfo("Europe/Istanbul")
except ZoneInfoNotFoundError:
    ISTANBUL_TIMEZONE = timezone(timedelta(hours=3))


def now_in_istanbul():
    """Return a timezone-naive timestamp in the application's business timezone."""
    return datetime.now(ISTANBUL_TIMEZONE).replace(tzinfo=None)


def now_in_utc():
    """Return a timezone-naive UTC timestamp for database storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_to_istanbul(value):
    """Convert a UTC database timestamp to a timezone-naive Istanbul timestamp."""
    if value is None or not isinstance(value, datetime):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.astimezone(ISTANBUL_TIMEZONE).replace(tzinfo=None)


def istanbul_to_utc(value):
    """Convert a timezone-naive Istanbul form timestamp to naive UTC for storage."""
    if value is None or not isinstance(value, datetime):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=ISTANBUL_TIMEZONE)
    else:
        value = value.astimezone(ISTANBUL_TIMEZONE)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def istanbul_day_start_utc(value):
    if isinstance(value, datetime):
        value = value.date()
    local_value = datetime.combine(value, time.min, tzinfo=ISTANBUL_TIMEZONE)
    return local_value.astimezone(timezone.utc).replace(tzinfo=None)


def istanbul_day_end_utc(value):
    if isinstance(value, datetime):
        value = value.date()
    local_value = datetime.combine(value, time.max, tzinfo=ISTANBUL_TIMEZONE)
    return local_value.astimezone(timezone.utc).replace(tzinfo=None)


def quantize_amount(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def start_of_day(value):
    if isinstance(value, datetime):
        value = value.date()
    return datetime.combine(value, time.min)


def end_of_day(value):
    if isinstance(value, datetime):
        value = value.date()
    return datetime.combine(value, time.max)


def parse_iso_date(value, fallback=None):
    if not value:
        return fallback or date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return fallback or date.today()


def is_ajax_request():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def is_modal_request():
    return request.args.get("modal") == "1" or request.headers.get("X-Modal-Request") == "1"
