import csv
import re
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse


OUTPUT_CLEAN = Path("clean.csv")
OUTPUT_ISSUES = Path("issues.csv")

CLEAN_FIELDS = [
    "record_id",
    "customer_id",
    "canonical_domain",
    "service",
    "billing_cycle_months",
    "amount_pkr",
    "registered_on",
    "renews_on",
    "status",
    "contact_email",
]

ISSUE_FIELDS = [
    "record_id",
    "field",
    "raw_value",
    "problem",
    "action_taken",
]


def parse_date(value):
    """Parse an unambiguous date and return YYYY-MM-DD.

    Ambiguous slash dates such as 01/02/2025 are rejected rather
    than silently guessing between day-first and month-first.
    """
    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]

    # Explicitly detect ambiguous numeric dates.
    match = re.fullmatch(
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
        value,
    )

    if match:
        first = int(match.group(1))
        second = int(match.group(2))

        # If both values can be valid month numbers, the order
        # cannot safely be inferred from the value alone.
        if 1 <= first <= 12 and 1 <= second <= 12:
            return None

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    return None


def parse_money(value):
    """Parse PKR amounts into Decimal with two decimal places.

    Parentheses represent negative/refund values.
    USD values are rejected because no exchange rate is supplied.
    """
    if value is None:
        return None

    raw = str(value).strip()

    if not raw:
        return None

    if re.search(r"\bUSD\b", raw, re.IGNORECASE):
        return None

    # Reject an explicit dollar sign as non-PKR.
    if "$" in raw:
        return None

    negative = raw.startswith("(") and raw.endswith(")")

    cleaned = raw
    cleaned = re.sub(r"(?i)\b(?:PKR|Rs\.?|Rupees)\b", "", cleaned)
    cleaned = cleaned.replace(",", "").replace(" ", "")
    cleaned = cleaned.strip()

    if negative:
        cleaned = cleaned[1:-1].strip()

    if not re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
        return None

    try:
        amount = Decimal(cleaned)

        if negative:
            amount = -amount

        return amount.quantize(Decimal("0.01"))

    except InvalidOperation:
        return None


def canonicalize_domain(value):
    """Normalize a domain into a lowercase hostname."""
    if value is None:
        return None

    value = str(value).strip().lower()

    if not value:
        return None

    if "://" not in value:
        value = "https://" + value

    try:
        parsed = urlparse(value)

        domain = parsed.hostname

        if not domain:
            return None

        domain = domain.lower().rstrip(".")

        if domain.startswith("www."):
            domain = domain[4:]

        if not domain:
            return None

        return domain

    except ValueError:
        return None


def normalize_cycle(value):
    """Convert common billing-cycle representations to months."""
    if value is None:
        return None

    raw = str(value).strip().lower()

    if not raw:
        return None

    raw = raw.replace("_", " ").replace("-", " ")

    match = re.fullmatch(r"(\d+)\s*(month|months|mo|mos)", raw)
    if match:
        return int(match.group(1))

    match = re.fullmatch(r"(\d+)\s*(year|years|yr|yrs)", raw)
    if match:
        return int(match.group(1)) * 12

    if raw.isdigit():
        number = int(raw)
        return number if number > 0 else None

    return None


def first_value(row, names):
    """Return the first non-empty value matching known column names."""
    normalized = {
        str(key).strip().lower().replace(" ", "_"): value
        for key, value in row.items()
    }

    for name in names:
        value = normalized.get(name)
        if value is not None and str(value).strip():
            return value

    return ""


def add_issue(issues, record_id, field, raw_value, problem, action):
    issues.append(
        {
            "record_id": record_id,
            "field": field,
            "raw_value": "" if raw_value is None else str(raw_value),
            "problem": problem,
            "action_taken": action,
        }
    )


def load_rows(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("Input CSV has no header row.")

        return list(reader)


def clean_rows(rows):
    clean = []
    issues = []

    for index, row in enumerate(rows, start=1):
        record_id = first_value(
            row,
            ["record_id", "id", "renewal_id"],
        ) or str(index)

        customer_id = first_value(
            row,
            ["customer_id", "customer", "customerid"],
        )

        domain_raw = first_value(
            row,
            ["domain", "domain_name", "website", "host"],
        )

        service = first_value(
            row,
            ["service", "product", "service_name"],
        )

        cycle_raw = first_value(
            row,
            [
                "billing_cycle_months",
                "billing_cycle",
                "cycle",
                "term",
            ],
        )

        amount_raw = first_value(
            row,
            [
                "amount_pkr",
                "amount",
                "renewal_amount",
                "price",
            ],
        )

        registered_raw = first_value(
            row,
            [
                "registered_on",
                "registration_date",
                "registered",
            ],
        )

        renews_raw = first_value(
            row,
            [
                "renews_on",
                "renewal_date",
                "renewal_on",
                "due_date",
            ],
        )

        status_raw = first_value(
            row,
            ["status", "state"],
        )

        email = first_value(
            row,
            ["contact_email", "email", "customer_email"],
        )

        canonical_domain = canonicalize_domain(domain_raw)

        if domain_raw and canonical_domain != str(domain_raw).strip().lower().removeprefix("www."):
            add_issue(
                issues,
                record_id,
                "domain",
                domain_raw,
                "domain formatting required normalization",
                f"canonicalized to {canonical_domain or 'invalid'}",
            )

        if not canonical_domain:
            add_issue(
                issues,
                record_id,
                "domain",
                domain_raw,
                "missing or malformed domain",
                "record flagged",
            )

        registered_on = parse_date(registered_raw)

        if registered_raw and not registered_on:
            add_issue(
                issues,
                record_id,
                "registered_on",
                registered_raw,
                "invalid or ambiguous date",
                "record flagged",
            )

        renews_on = parse_date(renews_raw)

        if renews_raw and not renews_on:
            add_issue(
                issues,
                record_id,
                "renews_on",
                renews_raw,
                "invalid or ambiguous date",
                "record flagged",
            )

        cycle = normalize_cycle(cycle_raw)

        if cycle_raw and cycle is None:
            add_issue(
                issues,
                record_id,
                "billing_cycle_months",
                cycle_raw,
                "invalid billing cycle",
                "record flagged",
            )

        amount = parse_money(amount_raw)

        if amount_raw and amount is None:
            if re.search(r"\bUSD\b|\$", str(amount_raw), re.IGNORECASE):
                problem = "non-PKR currency"
                action = "excluded from PKR total"
            else:
                problem = "invalid or malformed money value"
                action = "record flagged"

            add_issue(
                issues,
                record_id,
                "amount_pkr",
                amount_raw,
                problem,
                action,
            )

        status = status_raw.strip().lower() if status_raw else "active"

        status_aliases = {
            "active": "active",
            "paid": "paid",
            "pending": "pending",
            "cancelled": "cancelled",
            "canceled": "cancelled",
            "suspended": "suspended",
            "refunded": "refunded",
        }

        status = status_aliases.get(status, "flagged")

        if status == "flagged":
            add_issue(
                issues,
                record_id,
                "status",
                status_raw,
                "unknown status value",
                "normalized to flagged",
            )

        clean.append(
            {
                "record_id": record_id,
                "customer_id": customer_id,
                "canonical_domain": canonical_domain or "",
                "service": service,
                "billing_cycle_months": cycle or "",
                "amount_pkr": (
                    f"{amount:.2f}" if amount is not None else ""
                ),
                "registered_on": registered_on or "",
                "renews_on": renews_on or "",
                "status": status,
                "contact_email": email,
            }
        )

    return clean, issues


def write_csv(path, fieldnames, rows):
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    if len(sys.argv) != 2:
        print("Usage: python clean.py renewals_raw.csv")
        raise SystemExit(2)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        print(
            "TechAbout did not supply renewals_raw.csv, "
            "so Part A cannot be executed yet."
        )
        raise SystemExit(1)

    rows = load_rows(input_path)
    clean, issues = clean_rows(rows)

    write_csv(
        OUTPUT_CLEAN,
        CLEAN_FIELDS,
        clean,
    )

    write_csv(
        OUTPUT_ISSUES,
        ISSUE_FIELDS,
        issues,
    )

    status_totals = {}

    for row in clean:
        status = row["status"]
        status_totals[status] = status_totals.get(status, 0) + 1

    kept = len(clean)
    flagged = len(
        {
            issue["record_id"]
            for issue in issues
            if issue["action_taken"] == "record flagged"
        }
    )

    print(f"Rows in: {len(rows)}")
    print(f"Kept: {kept}")
    print(f"Dropped: 0")
    print(f"Flagged: {flagged}")
    print("Totals by status:")

    for status, count in sorted(status_totals.items()):
        print(f"  {status}: {count}")

    print(f"Wrote: {OUTPUT_CLEAN}")
    print(f"Wrote: {OUTPUT_ISSUES}")


if __name__ == "__main__":
    main()