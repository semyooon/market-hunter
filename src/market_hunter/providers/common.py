import hashlib
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit, urlunsplit


def listing_id(source: str, url: str) -> str:
    parsed = urlsplit(url)
    canonical = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
    return f"{source}_{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"


def now_utc() -> datetime:
    return datetime.now(UTC)


def parse_amount(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace("\xa0", " ")
    match = re.search(r"([0-9][0-9 .,'’]*)", cleaned)
    if not match:
        return None
    number = match.group(1).replace(" ", "").replace("'", "").replace("’", "")
    if number.count(",") == 1 and number.count(".") == 0:
        number = number.replace(",", ".")
    else:
        number = number.replace(",", "")
    try:
        return float(Decimal(number))
    except InvalidOperation:
        return None


def money_to_eur(amount: float | None, currency: str | None) -> float | None:
    if amount is None:
        return None
    # Deliberately conservative static conversions for ranking only; never present as an FX quote.
    conversion = {"EUR": 1.0, "€": 1.0, "BGN": 1 / 1.95583, "лв.": 1 / 1.95583, "USD": 0.92, "GBP": 1.17}
    return round(amount * conversion[currency or "EUR"], 2) if currency in conversion else None
