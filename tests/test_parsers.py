from clean import parse_date, parse_money, canonicalize_domain


def test_parse_date_iso():
    assert parse_date("2025-12-25") == "2025-12-25"


def test_parse_date_day_first():
    assert parse_date("25/12/2025") == "2025-12-25"


def test_parse_date_month_first():
    assert parse_date("12/25/2025") == "2025-12-25"


def test_parse_invalid_date():
    assert parse_date("31/02/2025") is None


def test_parse_blank_date():
    assert parse_date("") is None


def test_parse_money_with_rupees():
    assert parse_money("Rs 1,500") == 1500


def test_parse_money_with_pkr():
    assert parse_money("PKR 2,500") == 2500


def test_parse_money_with_parentheses():
    assert parse_money("(500)") == -500


def test_parse_blank_money():
    assert parse_money("") is None


def test_parse_usd():
    assert parse_money("USD 100") is None


def test_canonicalize_domain():
    assert canonicalize_domain("https://WWW.Example.com/") == "example.com"


def test_canonicalize_domain_without_protocol():
    assert canonicalize_domain("www.Example.com") == "example.com"


def test_canonicalize_domain_with_spaces():
    assert canonicalize_domain("  example.com  ") == "example.com"