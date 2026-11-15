"""Scrape every quote from quotes.toscrape.com and save it in four formats.

Run with no arguments:

    python scraper.py

The scraper starts at page 1, follows the "Next" link until the last page
(the page count is discovered, not hardcoded) and extracts every quote,
its author and its tags. (Work in progress: output files come next.)
"""

import logging
import random
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
BASE_URL = "http://quotes.toscrape.com/"
USER_AGENT = (
    "QuotesScraper/1.0 (educational data engineering project; "
    "python-requests)"
)
REQUEST_TIMEOUT = 10          # seconds to wait for a response
MAX_ATTEMPTS = 3              # 1 try + 2 retries
RETRY_WAIT = 3                # seconds to wait before retrying a request
MIN_DELAY = 1.0               # polite delay between requests, in seconds
MAX_DELAY = 2.0

OPENING_MARKS = ("“", '"')   # the quotation marks wrapping each quote
CLOSING_MARKS = ("”", '"')

log = logging.getLogger("scraper")


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
def create_session():
    """Return a requests session that sends a descriptive User-Agent."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def fetch_page(session, url):
    """Download one page and return its HTML, or None if every attempt fails.

    A failed request (connection error, timeout or HTTP error status) is
    retried up to MAX_ATTEMPTS times in total, waiting RETRY_WAIT seconds
    between attempts. No exception escapes this function.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            return response.text
        except requests.RequestException as error:
            log.warning("Attempt %d/%d failed for %s: %s",
                        attempt, MAX_ATTEMPTS, url, error)
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_WAIT)
    log.error("Giving up on %s after %d attempts", url, MAX_ATTEMPTS)
    return None


def polite_delay():
    """Sleep a random 1-2 seconds so the site is not hit too quickly."""
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def clean_quote_text(text):
    """Strip the surrounding quotation marks and whitespace from a quote.

    Only the outer pair is removed, so quotation marks inside the quote stay.
    """
    text = text.strip()
    if text.startswith(OPENING_MARKS):
        text = text[1:]
    if text.endswith(CLOSING_MARKS):
        text = text[:-1]
    return text.strip()


def parse_quotes(soup, page_number, scraped_at):
    """Extract every quote on one page as a list of record dictionaries."""
    records = []
    for block in soup.select("div.quote"):
        text = block.select_one("span.text")
        author = block.select_one("small.author")
        if text is None or author is None:
            log.warning("Skipping a malformed quote block on page %d",
                        page_number)
            continue
        records.append({
            "quote": clean_quote_text(text.get_text()),
            "author": author.get_text(strip=True),
            # A quote with no tags gets an empty list, not a missing field
            "tags": [tag.get_text(strip=True)
                     for tag in block.select("div.tags a.tag")],
            "page": page_number,
            "scraped_at": scraped_at,
        })
    return records


def find_next_url(soup, current_url):
    """Return the absolute URL of the next page, or None on the last page.

    The last page has no li.next element, so pagination ends when it is
    missing rather than after a fixed number of pages.
    """
    link = soup.select_one("li.next > a[href]")
    if link is None:
        return None
    return urljoin(current_url, link["href"])


# ---------------------------------------------------------------------------
# Scraping loop
# ---------------------------------------------------------------------------
def scrape_all_pages(session, start_url, scraped_at):
    """Follow the pagination from start_url and collect every quote.

    Returns (records, pages_fetched, error). error is None on success, or a
    message if a page could not be fetched; the quotes collected before that
    page are still returned so the run can stop cleanly.
    """
    records = []
    pages_fetched = 0
    url = start_url
    while url:
        if pages_fetched:
            polite_delay()
        html = fetch_page(session, url)
        if html is None:
            return records, pages_fetched, f"could not fetch {url}"
        pages_fetched += 1
        soup = BeautifulSoup(html, "html.parser")
        page_records = parse_quotes(soup, pages_fetched, scraped_at)
        records.extend(page_records)
        log.info("Page %d: %d quotes (%s)", pages_fetched,
                 len(page_records), url)
        url = find_next_url(soup, url)
    return records, pages_fetched, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def print_summary(pages_fetched, records, error):
    """Print pages fetched and quotes extracted."""
    print()
    print(f"Pages fetched:    {pages_fetched}")
    print(f"Quotes extracted: {len(records)}")
    print(f"Authors:          {len({r['author'] for r in records})}")
    if error:
        print(f"Stopped early:    {error}")


def main():
    """Scrape all pages and print a summary."""
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    scraped_at = datetime.now().isoformat(timespec="seconds")
    session = create_session()
    try:
        records, pages, error = scrape_all_pages(session, BASE_URL,
                                                 scraped_at)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    for record in records[:3]:
        print(record)
    print_summary(pages, records, error)
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
