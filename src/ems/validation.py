"""Validation shared by the console and service entry points."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation


def text(value, label, maximum, optional=False):
    value = str(value).strip()
    if optional and not value:
        return None
    if not value or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError(f"{label} must contain 1–{maximum} printable characters.")
    return value


def identifier(value, prefix):
    value = str(value).strip().upper()
    if not re.fullmatch(prefix + r"[0-9]{6}", value):
        raise ValueError(f"ID must be {prefix} followed by six digits.")
    return value


def day(value):
    value = str(value).strip()
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Date must use YYYY-MM-DD.")
    return date.fromisoformat(value)


def money(value):
    try:
        result = Decimal(str(value).strip())
    except InvalidOperation:
        raise ValueError("Amount must be a number.") from None
    if not result.is_finite() or not 0 <= result <= Decimal("9999999999.99"):
        raise ValueError("Amount must be between 0 and 9999999999.99.")
    if result != result.quantize(Decimal("0.01")):
        raise ValueError("Amount must have at most two decimal places.")
    return result.quantize(Decimal("0.01"))


def phone(value):
    value = str(value).strip()
    if not value:
        return None
    if not re.fullmatch(r"\+?[0-9]{7,15}", value):
        raise ValueError("Phone must contain 7–15 digits, optionally prefixed with +.")
    return value


def email(value):
    value = text(value, "Email", 100, optional=True)
    if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError("Enter a valid email address.")
    return value


def rating(value):
    value = str(value).strip()
    if not re.fullmatch(r"[0-9]", value):
        raise ValueError("Rating must be an integer from 0 to 9.")
    return int(value)


def username(value):
    value = str(value).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,20}", value):
        raise ValueError(
            "Username must contain 1–20 letters, digits, dots, underscores or hyphens."
        )
    return value
