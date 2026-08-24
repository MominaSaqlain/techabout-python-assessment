# TechAbout Python Developer Assessment

## Overview

This repository contains my solution for the TechAbout Python Developer assessment.

The assessment consists of two parts:

- Part A: PKHosting renewal data cleanup and analysis
- Part B: TECHi article metadata reader

Part A is currently waiting for the official `renewals_raw.csv` dataset because it was not included with the assessment materials. TechAbout Recruitment confirmed that the dataset was accidentally omitted.

Part B has been implemented, tested, and executed successfully.

---

## Requirements

- Python 3.10+
- requests
- beautifulsoup4
- pytest

Install the required packages with:

```bash
py -m pip install requests beautifulsoup4 pytest

Part A — PKHosting Renewals Cleanup
Status

The renewal-cleaning implementation is prepared in clean.py.

The official renewals_raw.csv file was not included with the assessment email or assessment page. TechAbout Recruitment confirmed that the dataset was missing and that Part A is paused until the file is provided.

I have not fabricated renewal data or totals without the official source dataset.

Once renewals_raw.csv is provided, the script can be executed with:

python clean.py renewals_raw.csv

The expected outputs are:

clean.csv
issues.csv
stdout summary

The cleaning process is designed to:

Normalize dates
Normalize monetary values
Canonicalize domains
Normalize billing-cycle values
Handle duplicates
Surface invalid or ambiguous records
Record every changed, dropped, merged, or flagged record in issues.csv
Produce a summary of rows processed and totals by status
Part B — TECHi Metadata Reader

The techi_audit.py script discovers published TECHi article URLs through robots.txt and sitemap information rather than hardcoding article paths.

The scraper:

Reads robots.txt
Checks robots.txt permissions before fetching URLs
Uses a descriptive User-Agent
Maintains a one-request-per-second delay between network requests
Uses a disk cache so repeated runs avoid unnecessary network requests
Handles timeouts and HTTP errors gracefully
Handles absolute and relative date formats
Extracts article metadata
Collects up to 20 articles

The generated output is:

techi_articles.csv

The CSV contains:

url
slug
title
category
author_handle
date_text
date_iso
Execution

Run the scraper with:

py techi_audit.py

The assessment run successfully collected 20 articles.

The generated CSV was checked for missing required metadata.

Result:

Rows: 20
Missing title: 0
Missing category: 0
Missing author: 0
Missing date: 0
Tests

Offline pytest tests were added for parser behavior involving awkward inputs, including:

Date parsing
Money parsing
Domain normalization

Tests were executed with:

py -m pytest -q

Result:

13 passed

The tests are offline and do not require network access.

Design Decisions
URL Discovery

Article URLs are discovered through robots.txt and sitemap information rather than hardcoding article paths.

The scraper filters out obvious non-article URLs such as API endpoints, media files, feeds, category pages, tag pages, author pages, and static files.

Request Politeness

The scraper uses a descriptive User-Agent and a one-second delay between network requests.

A disk cache is used so that previously fetched pages can be reused on subsequent runs without making unnecessary requests.

Date Handling

Absolute dates are normalized to ISO format:

YYYY-MM-DD

Relative dates such as:

Updated 6 days ago

are converted into an ISO date.

Error Handling

The scraper handles:

Request timeouts
HTTP errors
404 responses
Invalid sitemap XML
Unexpected or incomplete article markup

A failure for one URL does not stop the complete collection process.

Part A — Judgement and Assumptions

The final renewal rules and totals will be documented in NOTES.md after the official renewals_raw.csv is provided.

The ambiguous-date rule and duplicate-record rule will be applied consistently and documented before calculating the renewal totals.

No renewal total has been fabricated without the official source dataset.

Project Structure
techabout-python-assessment/
│
├── clean.py
├── techi_audit.py
├── techi_articles.csv
├── tests/
│   └── ...
├── README.md
├── NOTES.md
│
└── renewals_raw.csv
    # Pending from TechAbout
What I Would Improve With More Time

With additional time, I would:

Add more parser edge cases and validation tests
Add saved HTML fixtures for offline scraper testing
Expand extraction support for additional article markup variations
Add stronger validation for the generated CSV schemas
Add more structured logging
Complete and verify Part A immediately after receiving the official renewal dataset
Current Assessment Status

Part B has been implemented, tested, and executed successfully.

Part A is currently blocked only by the missing renewals_raw.csv dataset. This has already been reported to TechAbout Recruitment, and they confirmed that the file was accidentally omitted from the assessment materials.