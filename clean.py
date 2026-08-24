import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse


def parse_date(value):
    """
    Convert supported date formats into ISO format (YYYY-MM-DD).
    Return None when the value is blank or invalid.
    """
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    return None


def parse_money(value):
    """
    Parse common PKR money formats.

    Examples:
        Rs 1,500       -> 1500.00
        PKR 2,000      -> 2000.00
        (500)          -> -500.00
        1500           -> 1500.00
    """
    if value is None:
        return None

    raw = str(value).strip()

    if not raw:
        return None

    # USD values are intentionally rejected here because
    # the assessment requires PKR amounts.
    if re.search(r"\bUSD\b|\$", raw, re.IGNORECASE):
        return None

    negative = raw.startswith("(") and raw.endswith(")")

    cleaned = re.sub(r"[^\d.]", "", raw)

    if not cleaned:
        return None

    try:
        amount = Decimal(cleaned)

        if negative:
            amount = -amount

        return amount.quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def canonicalize_domain(value):
    """
    Normalize a domain into a canonical lowercase hostname.
    """
    if value is None:
        return None

    value = str(value).strip().lower()

    if not value:
        return None

    if "://" not in value:
        value = "https://" + value

    try:
        parsed = urlparse(value)
        domain = parsed.netloc.split("@")[-1].split(":")[0]

        if domain.startswith("www."):
            domain = domain[4:]

        return domain.rstrip(".") or None

    except ValueError:
        return None