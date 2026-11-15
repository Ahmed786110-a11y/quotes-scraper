"""Scrape every quote from quotes.toscrape.com and save it in four formats.

Run with no arguments:

    python scraper.py

The scraper starts at page 1, follows the "Next" link until the last page
(the page count is discovered, not hardcoded), and writes the same records
to output/quotes.json, output/quotes.csv, output/quotes.txt and
output/quotes.yaml. Each run overwrites the four files.
"""

import csv
import json
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml
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

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_NAME = "quotes"
FIELDS = ["quote", "author", "tags", "page", "scraped_at"]
CSV_TAG_SEPARATOR = ";"
TEXT_TAG_SEPARATOR = ", "
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
# Writing the four output files
# ---------------------------------------------------------------------------
def write_json(records, path):
    """Write the records as one JSON array indented two spaces."""
    with open(path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)
        file.write("\n")


def write_csv(records, path):
    """Write one CSV row per quote, tags joined with semicolons.

    The csv module escapes commas and quotation marks inside the text.
    """
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["tags"] = CSV_TAG_SEPARATOR.join(record["tags"])
            writer.writerow(row)


def write_text(records, path):
    """Write one labelled block per quote, with a blank line between blocks."""
    blocks = []
    for record in records:
        blocks.append("\n".join([
            f"Quote: {record['quote']}",
            f"Author: {record['author']}",
            f"Tags: {TEXT_TAG_SEPARATOR.join(record['tags'])}",
            f"Page: {record['page']}",
            f"Scraped: {record['scraped_at']}",
        ]))
    with open(path, "w", encoding="utf-8") as file:
        # rstrip() avoids a trailing space on "Tags: " when a quote has none
        file.write("\n\n".join(
            "\n".join(line.rstrip() for line in block.splitlines())
            for block in blocks))
        file.write("\n")


def write_yaml(records, path):
    """Write the records as a YAML list of mappings with yaml.safe_dump."""
    with open(path, "w", encoding="utf-8") as file:
        yaml.safe_dump(records, file, sort_keys=False, allow_unicode=True,
                       default_flow_style=False)


WRITERS = {
    "json": write_json,
    "csv": write_csv,
    "txt": write_text,
    "yaml": write_yaml,
}


def write_outputs(records, output_dir):
    """Write all four formats (overwriting old files); return the paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for extension, writer in WRITERS.items():
        path = output_dir / f"{OUTPUT_NAME}.{extension}"
        writer(records, path)
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def print_summary(pages_fetched, records, written, error):
    """Print pages fetched, quotes extracted and files written."""
    print()
    print("=" * 50)
    print("Scrape summary")
    print("=" * 50)
    print(f"Pages fetched:    {pages_fetched}")
    print(f"Quotes extracted: {len(records)}")
    print(f"Authors:          {len({r['author'] for r in records})}")
    print(f"Files written:    {len(written)}")
    for path in written:
        print(f"  - {path}")
    if error:
        print(f"Stopped early:    {error}")
    print("=" * 50)


def main():
    """Scrape all pages, write the output files and print a summary."""
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    scraped_at = datetime.now().isoformat(timespec="seconds")
    session = create_session()

    try:
        records, pages, error = scrape_all_pages(session, BASE_URL,
                                                 scraped_at)
    except KeyboardInterrupt:
        print("\nInterrupted by user - no files written.")
        return 130

    written = []
    if records:
        try:
            written = write_outputs(records, OUTPUT_DIR)
        except OSError as os_error:
            error = f"could not write output files: {os_error}"
    else:
        # Keep the previous output files rather than overwrite them
        error = error or "no quotes found"

    print_summary(pages, records, written, error)
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
