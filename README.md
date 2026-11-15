# Quotes Scraper

Scrapes every quote from [quotes.toscrape.com](http://quotes.toscrape.com/) and writes the same records to four formats: JSON, CSV, plain text and YAML.

**Course:** DATA 430, Project 3 (Web Scraping and Multi-Format Output) · **Author:** Ahmed

## What it does

`scraper.py` starts at page 1 and follows the **Next** link until the last page, which has no `li.next` element, so the number of pages is discovered rather than hardcoded. For every quote it extracts the text, the author and the full tag list, then writes the results to `output/`.

The scraper is polite and robust:

- sends a descriptive `User-Agent` header
- waits a random 1 to 2 seconds between requests
- retries a failed request (connection error, timeout or HTTP error) twice, so three attempts in total
- if a page still fails, it stops cleanly with a message instead of crashing, and writes the quotes collected so far
- if no quotes could be collected at all, it leaves the existing output files untouched

## Requirements

- Python 3.8 or later
- The libraries in `requirements.txt`: `requests`, `beautifulsoup4` and `PyYAML`

## Installation

```
git clone https://github.com/<Ahmed786110-a11y>/quotes-scraper.git
cd quotes-scraper
```

Optionally create and activate a virtual environment:

```
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
source .venv/bin/activate         # macOS / Linux
```

Install the dependencies:

```
python -m pip install -r requirements.txt
```

**Note for very new Python versions (for example 3.15 on Windows):** if installing PyYAML fails with "Microsoft Visual C++ 14.0 or greater is required", install it without its optional C extension, which PyYAML does not need:

```
$env:PYYAML_FORCE_LIBYAML = "0"     # Windows PowerShell
export PYYAML_FORCE_LIBYAML=0       # macOS / Linux
python -m pip install -r requirements.txt
```

## Usage

```
python scraper.py
```

No arguments or edits are needed. A full run takes about 15–20 seconds because of the polite delay, and ends with a summary of pages fetched, quotes extracted and files written. The exit code is 0 on success and 1 if the run stopped early.

## Output

Each run overwrites these four files in `output/`. All four hold the same records in the same order.

| File | Format |
| --- | --- |
| `quotes.json` | One JSON array of objects, indented two spaces (the canonical shape) |
| `quotes.csv` | Header `quote,author,tags,page,scraped_at`, one row per quote, tags joined with `;` |
| `quotes.txt` | One block per quote with `Quote:`, `Author:`, `Tags:`, `Page:` and `Scraped:` lines, blank line between blocks |
| `quotes.yaml` | A list of mappings written with `yaml.safe_dump` |

Every record has five fields:

```json
{
  "quote": "The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.",
  "author": "Albert Einstein",
  "tags": ["change", "deep-thoughts", "thinking", "world"],
  "page": 1,
  "scraped_at": "2026-11-15T06:56:12"
}
```

- `quote` has its surrounding quotation marks and whitespace removed
- `tags` is an empty list when a quote has no tags
- `page` is the page the quote was found on
- `scraped_at` is the ISO 8601 time the run started, the same for every record in a run

## Project structure

```
quotes-scraper/
├── scraper.py          # the scraper
├── requirements.txt    # requests, beautifulsoup4, PyYAML
├── output/
│   ├── quotes.json
│   ├── quotes.csv
│   ├── quotes.txt
│   └── quotes.yaml
├── README.md
└── .gitignore          # __pycache__/ and virtual environments
```

## Configuration

Settings such as the start URL, User-Agent, timeout, number of attempts, delay range and output folder are constants at the top of `scraper.py`.
