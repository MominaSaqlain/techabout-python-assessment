# Assessment Notes

## Part A — PKHosting Renewals

### Dataset status

The assessment brief states that `renewals_raw.csv` contains 34 renewal records.

However, the official `renewals_raw.csv` file was not included in the assessment email or on the assessment page. TechAbout Recruitment confirmed that the file was accidentally omitted and that Part A is paused until the dataset is provided.

For that reason, I have not generated or invented renewal totals without the official source data.

Once the dataset is provided, the same documented rules below will be applied to the supplied records.

---

## Ambiguous Date Rule

The source data may contain both day-first and month-first formats, for example:

- `25/12/2025`
- `12/25/2025`

The rule is:

1. If only one interpretation is possible, use that interpretation.
2. If both interpretations are possible, use the date convention supported by the surrounding dataset/context rather than silently guessing.
3. If the intended date cannot be determined reliably, flag the record in `issues.csv` rather than silently choosing a date.
4. All accepted dates will be stored in ISO format:

`YYYY-MM-DD`

This keeps date handling explicit and auditable.

---

## Money Rule

Amounts may contain:

- Currency symbols
- Thousands separators
- Parentheses
- Blank values
- Negative/refund values
- A USD-denominated line

PKR amounts will be normalized to a numeric `amount_pkr` value.

Blank or malformed amounts will be surfaced in `issues.csv`.

The USD record will not be silently converted because the assessment does not provide an exchange rate or conversion date. It will therefore be excluded from PKR renewal totals and documented as an exclusion.

---

## Domain Rule

Domains will be canonicalized by:

- Removing surrounding whitespace
- Converting the hostname to lowercase
- Removing URL schemes such as `http://` and `https://`
- Removing a leading `www.`
- Removing paths, query strings, and fragments where appropriate
- Removing unnecessary trailing dots

The resulting value will represent the canonical domain.

Malformed domains will be flagged in `issues.csv`.

---

## Duplicate Rule

Duplicate renewal records will be identified using the strongest available combination of fields, including customer, canonical domain, service, renewal information, and other identifying values.

When duplicate records represent the same renewal:

- The record with the most complete and internally consistent information will be retained.
- Duplicate records will not disappear silently.
- Every merged or removed duplicate will be recorded in `issues.csv`.

If two duplicate records contain different amounts, the difference will be investigated rather than automatically summing both values.

The final decision will be documented against the actual supplied records.

---

## Status Rule

The final status values will use a fixed, documented set.

Records representing cancelled or suspended services will not be treated as active payable renewals unless the supplied data provides evidence that they should still be included.

Any such exclusion will be recorded in `issues.csv`.

---

## Renewal Window

The assessment asks for PKR renewals due between:

`2026-08-03` and `2026-09-02`

The calculation will include the stated dates as an inclusive range.

Only eligible PKR renewal records will be included.

The following will be reviewed explicitly before calculating the total:

- Cancelled services
- Suspended services
- Refund/negative amounts
- Duplicate records with conflicting amounts
- The USD-denominated record
- Invalid or ambiguous dates

No total is reported yet because the official `renewals_raw.csv` dataset is missing.

---

# Part B — TECHi Metadata Reader

The TECHi scraper discovers URLs through `robots.txt` and sitemap information instead of hardcoding article paths.

The scraper:

- Uses a descriptive User-Agent
- Checks robots.txt permissions
- Maintains a one-second delay between network requests
- Uses disk caching for repeated runs
- Handles timeouts and HTTP errors gracefully
- Handles unexpected markup without stopping the complete run
- Collects a maximum of 20 articles

The final run successfully collected 20 articles.

The generated `techi_articles.csv` contains all required fields.

Validation result:

- Rows: 20
- Missing titles: 0
- Missing categories: 0
- Missing authors: 0
- Missing dates: 0

---

# Testing

Offline parser tests were executed with:

```bash
py -m pytest -q

Result:

13 passed

The tests cover awkward date, money, and domain inputs without requiring network access.

Current Limitation

Part A cannot be completed or numerically verified until TechAbout provides the official renewals_raw.csv.

I have intentionally not fabricated sample renewal data or a renewal total because doing so would make the assessment result unreliable.

Once the dataset is supplied, I will run the cleaning script, inspect every flagged/changed record, calculate the renewal-window total, and update the generated CSV outputs.