"""
Validators — Input validation helpers.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


def validate_amount(text: str, min_val: float = 0.01, max_val: float = 100000.0) -> tuple[bool, float, str]:
    """
    Validate a monetary amount string.
    Returns (valid, parsed_value, error_message)
    """
    try:
        value = float(text.strip().replace(",", "."))
    except (ValueError, AttributeError):
        return False, 0.0, "❌ Please enter a valid number."
    if value < min_val:
        return False, 0.0, f"❌ Minimum amount is ${min_val:.2f}."
    if value > max_val:
        return False, 0.0, f"❌ Maximum amount is ${max_val:.2f}."
    return True, round(value, 2), ""


def validate_promo_code(code: str) -> tuple[bool, str, str]:
    """Returns (valid, normalized_code, error_message)."""
    code = code.strip().upper()
    if not code:
        return False, "", "❌ Code cannot be empty."
    if len(code) < 3 or len(code) > 30:
        return False, "", "❌ Code must be 3–30 characters."
    if not re.match(r"^[A-Z0-9_\-]+$", code):
        return False, "", "❌ Code can only contain letters, digits, _ and -."
    return True, code, ""


def validate_product_price(text: str) -> tuple[bool, float, str]:
    return validate_amount(text, min_val=0.01, max_val=99999.99)


def validate_stock(text: str) -> tuple[bool, int, str]:
    try:
        value = int(text.strip())
        if value < 0:
            return False, 0, "❌ Stock cannot be negative."
        if value > 1_000_000:
            return False, 0, "❌ Stock is too large."
        return True, value, ""
    except ValueError:
        return False, 0, "❌ Please enter a whole number."


def validate_discount(text: str, discount_type: str) -> tuple[bool, float, str]:
    try:
        value = float(text.strip())
        if discount_type == "percentage":
            if not (0 < value <= 100):
                return False, 0.0, "❌ Percentage must be 1–100."
        else:
            if value <= 0:
                return False, 0.0, "❌ Discount must be positive."
        return True, round(value, 2), ""
    except ValueError:
        return False, 0.0, "❌ Please enter a valid number."


def validate_date(text: str) -> tuple[bool, str, str]:
    """Validate date input as YYYY-MM-DD and return ISO format."""
    text = text.strip()
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            dt = dt.replace(tzinfo=timezone.utc, hour=23, minute=59, second=59)
            if dt < datetime.now(timezone.utc):
                return False, "", "❌ Date must be in the future."
            return True, dt.isoformat(), ""
        except ValueError:
            continue
    return False, "", "❌ Invalid date. Use YYYY-MM-DD format."


def validate_text_length(text: str, min_len: int = 1, max_len: int = 1000) -> tuple[bool, str]:
    text = text.strip()
    if len(text) < min_len:
        return False, f"❌ Text too short (minimum {min_len} characters)."
    if len(text) > max_len:
        return False, f"❌ Text too long (maximum {max_len} characters)."
    return True, ""
