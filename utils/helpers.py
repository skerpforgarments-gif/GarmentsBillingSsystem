from datetime import datetime


# =========================================================
# SAFE CONVERSIONS
# =========================================================
def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_str(value, default=""):
    return str(value) if value is not None else default


# =========================================================
# DATE HELPERS
# =========================================================
def today():
    return datetime.now().strftime("%Y-%m-%d")


def format_date(date_str, output_format="%d-%m-%Y"):
    """
    Input: 2025-01-01
    Output: 01-01-2025
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime(output_format)
    except:
        return date_str


# =========================================================
# CURRENCY HELPERS
# =========================================================
def format_currency(amount):
    try:
        return f"₹{round(float(amount), 2)}"
    except:
        return "₹0.00"


# =========================================================
# VALIDATION
# =========================================================
def is_empty(value):
    return value in [None, "", [], {}]


def required(value, field_name="Field"):
    if is_empty(value):
        return f"{field_name} is required"
    return None


# =========================================================
# DICT HELPERS
# =========================================================
def safe_get(data: dict, key, default=None):
    return data.get(key, default) if isinstance(data, dict) else default


# =========================================================
# ID HELPERS
# =========================================================
def ensure_int_id(value):
    try:
        return int(value)
    except:
        return None


# =========================================================
# SUM HELPER
# =========================================================
def sum_by_key(data, key):
    return sum(to_float(item.get(key, 0)) for item in data)
