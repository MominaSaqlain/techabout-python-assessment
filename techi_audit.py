import csv
import hashlib
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.techi.com/"
ROBOTS_URL = urljoin(BASE_URL, "robots.txt")

OUTPUT_FILE = Path("techi_articles.csv")
CACHE_DIR = Path(".cache")

MAX_ARTICLES = 20
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 15

USER_AGENT = (
    "TechAboutAssessmentBot/1.0 "
    "(Python Developer assessment; polite metadata reader)"
)


def create_session():
    """Create one HTTP session with a descriptive User-Agent."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def cache_path(url):
    """Return a deterministic cache filename for a URL."""
    filename = hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html"
    return CACHE_DIR / filename


def fetch_text(session, url, use_cache=True):
    """
    Fetch a URL as text.

    Cached responses are reused on later runs.
    Network requests are separated by at least one second.
    """
    CACHE_DIR.mkdir(exist_ok=True)

    path = cache_path(url)

    if use_cache and path.exists():
        return path.read_text(
            encoding="utf-8",
            errors="replace"
        )

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code == 404:
            print(f"404: {url}")
            return None

        response.raise_for_status()

        text = response.text

        path.write_text(
            text,
            encoding="utf-8"
        )

        time.sleep(REQUEST_DELAY)

        return text

    except requests.RequestException as exc:
        print(f"Request failed for {url}: {exc}")
        return None


def load_robots(session):
    """Read robots.txt and create a RobotFileParser."""
    robots_text = fetch_text(session, ROBOTS_URL)

    if not robots_text:
        return None, None

    robots = RobotFileParser()
    robots.set_url(ROBOTS_URL)
    robots.parse(robots_text.splitlines())

    return robots_text, robots


def extract_sitemap_urls(robots_text):
    """
    Discover sitemap URLs from robots.txt.

    Sitemap URLs are therefore not hardcoded.
    """
    sitemap_urls = []

    for line in robots_text.splitlines():
        if line.lower().startswith("sitemap:"):
            sitemap = line.split(":", 1)[1].strip()

            if sitemap:
                sitemap_urls.append(
                    urljoin(BASE_URL, sitemap)
                )

    return sitemap_urls


def parse_sitemap(xml_text):
    """Extract URLs from a sitemap XML document."""
    urls = []

    try:
        root = ET.fromstring(xml_text)

        for element in root.iter():
            if element.tag.endswith("loc") and element.text:
                urls.append(element.text.strip())

    except ET.ParseError as exc:
        print(f"Could not parse sitemap XML: {exc}")

    return urls


def is_article_url(url):
    """
    Filter out obvious non-article URLs such as media,
    API endpoints and taxonomy pages.
    """
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip("/")

    if not path:
        return False

    blocked_paths = (
        "/api/",
        "/wp-content/",
        "/wp-json/",
        "/feed/",
        "/category/",
        "/tag/",
        "/author/",
    )

    blocked_extensions = (
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".svg",
        ".xml",
        ".pdf",
        ".mp4",
        ".webm",
    )

    if any(path.startswith(prefix) for prefix in blocked_paths):
        return False

    if path.endswith(blocked_extensions):
        return False

    return True


def discover_article_urls(session, robots_text, robots):
    """
    Discover candidate article URLs through robots.txt -> sitemap.

    Handles both sitemap indexes and nested sitemaps.
    """
    sitemap_urls = extract_sitemap_urls(robots_text)

    if not sitemap_urls:
        print("No sitemap was advertised in robots.txt.")
        return []

    article_urls = []

    for sitemap_url in sitemap_urls:

        if not robots.can_fetch(USER_AGENT, sitemap_url):
            print(f"Blocked by robots.txt: {sitemap_url}")
            continue

        sitemap_text = fetch_text(
            session,
            sitemap_url
        )

        if not sitemap_text:
            continue

        urls = parse_sitemap(sitemap_text)

        for url in urls:

            if url.endswith(".xml") or "sitemap" in url.lower():

                if not robots.can_fetch(USER_AGENT, url):
                    continue

                nested_text = fetch_text(
                    session,
                    url
                )

                if nested_text:
                    article_urls.extend(
                        parse_sitemap(nested_text)
                    )

            else:
                article_urls.append(url)

            if len(article_urls) >= MAX_ARTICLES * 5:
                break

        if len(article_urls) >= MAX_ARTICLES * 5:
            break

    # Keep only likely article pages.
    unique_urls = []

    for url in article_urls:

        if not url.startswith(("http://", "https://")):
            continue

        if not is_article_url(url):
            continue

        if url not in unique_urls:
            unique_urls.append(url)

        if len(unique_urls) >= MAX_ARTICLES:
            break

    return unique_urls


def parse_relative_date(text, today=None):
    """
    Convert relative dates such as:

        Updated 6 days ago
        2 days ago
        1 week ago

    into YYYY-MM-DD.
    """
    if not text:
        return None

    if today is None:
        today = datetime.now(timezone.utc).date()

    match = re.search(
        r"(?:updated\s+)?(\d+)\s+"
        r"(day|days|week|weeks)\s+ago",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()

    days = amount * 7 if "week" in unit else amount

    return (
        today - timedelta(days=days)
    ).isoformat()


def parse_absolute_date(text):
    """Try common date formats and return ISO format."""
    if not text:
        return None

    text = text.strip()

    formats = [
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt
            ).date().isoformat()

        except ValueError:
            continue

    return None


def extract_date(soup):
    """Extract date text and normalize it to ISO format."""
    candidates = []

    selectors = [
        ("time", {}),
        ("meta", {"property": "article:published_time"}),
        ("meta", {"property": "article:modified_time"}),
        ("meta", {"name": "date"}),
    ]

    for tag_name, attributes in selectors:

        tag = soup.find(
            tag_name,
            attributes
        )

        if tag:

            value = (
                tag.get("datetime")
                or tag.get("content")
                or tag.get_text(
                    " ",
                    strip=True
                )
            )

            if value:
                candidates.append(value)

    for value in candidates:

        relative = parse_relative_date(value)

        if relative:
            return value, relative

        absolute = parse_absolute_date(value)

        if absolute:
            return value, absolute

        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            return value, parsed.date().isoformat()

        except ValueError:
            pass

    return None, None


def extract_category(soup):
    """Extract category from common article markup."""
    selectors = [
        '[rel="category tag"]',
        ".cat-links a",
        ".category a",
        'a[href*="/category/"]',
    ]

    for selector in selectors:

        tag = soup.select_one(selector)

        if tag:
            text = tag.get_text(
                " ",
                strip=True
            )

            if text:
                return text

    return None


def extract_author(soup):
    """Extract author name or handle."""
    selectors = [
        '[rel="author"]',
        ".author a",
        ".byline a",
        ".author-name",
    ]

    for selector in selectors:

        tag = soup.select_one(selector)

        if tag:

            text = tag.get_text(
                " ",
                strip=True
            )

            if text:
                return text

    return None


def extract_title(soup):
    """Extract article title."""
    selectors = [
        "h1",
        "meta[property='og:title']",
        "title",
    ]

    for selector in selectors:

        tag = soup.select_one(selector)

        if not tag:
            continue

        if tag.name == "meta":
            value = tag.get("content")
        else:
            value = tag.get_text(
                " ",
                strip=True
            )

        if value:
            return value

    return None


def extract_slug(url):
    """Extract the final URL path component."""
    path = urlparse(url).path.strip("/")

    if not path:
        return None

    return path.split("/")[-1]


def parse_article(url, html):
    """Extract all required metadata from an article."""
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    date_text, date_iso = extract_date(soup)

    return {
        "url": url,
        "slug": extract_slug(url),
        "title": extract_title(soup),
        "category": extract_category(soup),
        "author_handle": extract_author(soup),
        "date_text": date_text,
        "date_iso": date_iso,
    }


def write_articles(rows):
    """Write article metadata to the required CSV."""
    fieldnames = [
        "url",
        "slug",
        "title",
        "category",
        "author_handle",
        "date_text",
        "date_iso",
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)


def main():
    session = create_session()

    robots_text, robots = load_robots(session)

    if not robots_text or robots is None:
        print(
            "Unable to safely read robots.txt. Exiting."
        )
        return

    urls = discover_article_urls(
        session,
        robots_text,
        robots
    )

    if not urls:
        print("No article URLs discovered.")
        write_articles([])
        return

    rows = []

    for url in urls:

        if len(rows) >= MAX_ARTICLES:
            break

        if not robots.can_fetch(
            USER_AGENT,
            url
        ):
            print(
                f"Blocked by robots.txt: {url}"
            )
            continue

        html = fetch_text(
            session,
            url
        )

        if not html:
            continue

        try:

            article = parse_article(
                url,
                html
            )

            rows.append(article)

            print(
                f"Parsed: {url}"
            )

        except Exception as exc:

            print(
                f"Could not parse {url}: {exc}"
            )

    write_articles(rows)

    print(
        f"Collected {len(rows)} article(s)."
    )


if __name__ == "__main__":
    main()