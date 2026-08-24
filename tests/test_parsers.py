from decimal import Decimal

from clean import parse_date, parse_money, canonicalize_domain, normalize_cycle


def test_parse_date_iso():
    assert parse_date("2025-12-25") == "2025-12-25"


def test_parse_date_day_first_unambiguous():
    assert parse_date("25/12/2025") == "2025-12-25"


def test_parse_date_month_first_unambiguous():
    assert parse_date("12/25/2025") == "2025-12-25"


def test_parse_date_ambiguous_is_rejected():
    assert parse_date("01/02/2025") is None


def test_parse_invalid_date():
    assert parse_date("31/02/2025") is None


def test_parse_blank_date():
    assert parse_date("") is None


def test_parse_money_with_rupees():
    assert parse_money("Rs 1,500") == Decimal("1500.00")


def test_parse_money_with_pkr():
    assert parse_money("PKR 2,500") == Decimal("2500.00")


def test_parse_money_with_parentheses():
    assert parse_money("(500)") == Decimal("-500.00")


def test_parse_money_with_decimal():
    assert parse_money("Rs 1,250.75") == Decimal("1250.75")


def test_parse_blank_money():
    assert parse_money("") is None


def test_parse_usd():
    assert parse_money("USD 100") is None


def test_parse_dollar_sign():
    assert parse_money("$100") is None


def test_canonicalize_domain():
    assert (
        canonicalize_domain("https://WWW.Example.com/")
        == "example.com"
    )


def test_canonicalize_domain_without_protocol():
    assert canonicalize_domain("www.Example.com") == "example.com"


def test_canonicalize_domain_with_spaces():
    assert canonicalize_domain("  example.com  ") == "example.com"


def test_canonicalize_domain_with_path():
    assert (
        canonicalize_domain(
            "https://www.Example.com/some/page?x=1"
        )
        == "example.com"
    )


def test_canonicalize_domain_trailing_dot():
    assert canonicalize_domain("Example.com.") == "example.com"


def test_invalid_domain():
    assert canonicalize_domain("") is None


def test_normalize_cycle_months():
    assert normalize_cycle("12 months") == 12


def test_normalize_cycle_year():
    assert normalize_cycle("1 year") == 12


def test_normalize_cycle_numeric():
    assert normalize_cycle("6") == 6


def test_invalid_cycle():
    assert normalize_cycle("forever") is None