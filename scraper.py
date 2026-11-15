"""Scrape every quote from quotes.toscrape.com and save it in four formats.

Run with no arguments:

    python scraper.py

The scraper starts at page 1, follows the "Next" link until the last page
(the page count is discovered, not hardcoded).

Work in progress: this version only walks through the pages.
"""

import logging
import random
import sys
import time
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
# Pagination
# ---------------------------------------------------------------------------
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
def crawl_pages(session, start_url):
    """Follow the pagination from start_url until there is no next page.

    Returns (pages_fetched, error). error is None on success, or a message
    if a page could not be fetched.
    """
    pages_fetched = 0
    url = start_url
    while url:
        if pages_fetched:
            polite_delay()
        html = fetch_page(session, url)
        if html is None:
            return pages_fetched, f"could not fetch {url}"
        pages_fetched += 1
        soup = BeautifulSoup(html, "html.parser")
        log.info("Page %d fetched (%s)", pages_fetched, url)
        url = find_next_url(soup, url)
    return pages_fetched, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    """Walk through every page and print how many were fetched."""
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    session = create_session()
    try:
        pages, error = crawl_pages(session, BASE_URL)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    print(f"\nPages fetched: {pages}")
    if error:
        print(f"Stopped early: {error}")
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
