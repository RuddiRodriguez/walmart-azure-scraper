# Walmart location-aware catalog scraper

Python scraper with local Chrome, configurable stores/categories, transactional checkpoints,
source evidence, validation and atomic publication. No paid proxies or scraping APIs.

## Current status

October 23 review: see `WORK_LOG.md` and `docs/REVIEW_STATUS.md` for the latest evidence and gaps.
Run `python review_package.py` to re-audit the historical demonstration and generate checksums.
This is an offline audit, not a fresh scrape. `check_review_changes.py` uses explicitly synthetic
availability variants and an offline checkpoint check.

The included **500-product evidence dataset** came from the preceding live feasibility scripts,
not from a completed full-catalog run of this new runner. All 11 requested parent categories
are represented; Store 100 pickup, seller and prices were checked on product pages.
The latest packaged runner completed a fresh live 33-product sample across all 11 categories,
including intentional product-stage stop/resume; see `evidence/review-live/`. An earlier 22-product
sample remains in `evidence/live-smoke/`. The full-catalog runner and Azure installation/scheduling files are included. End-to-end catalog
coverage, live volume/digital offers and Azure execution still require acceptance testing.
Do not describe this version as already accepted or production-proven.

## Local setup

Install Chrome and Python 3.11+. macOS or Linux supported; Windows requires adapting the file lock.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scrape.py --store 100 --sample 2
```

Sample mode discovers at least the requested number of listing candidates per category, then checks
products until that many accepted records per category are available or candidates are exhausted.
It writes evidence but **never publishes production output**. Its nested `sample_validation` reports
only sample checks; pending full-catalog queues remain visible in the main report.

Full crawl:

```bash
.venv/bin/python scrape.py --store 100
```

Resume the same mode and configuration after interruption:

```bash
.venv/bin/python scrape.py --store 100 --resume
# For an interrupted sample:
.venv/bin/python scrape.py --store 100 --sample 2 --resume
```

## Files and flow

1. `config/categories.csv` supplies every requested parent category.
2. `config/stores.json` supplies store number, ZIP, expected name/address, canary URLs and thresholds.
3. `browser.py` selects pickup, checks the location, loads pages and detects blocking.
4. `extract.py` discovers child category links, reads offers and preserves displayed values.
5. `storage.py` stores page/product checkpoints in SQLite transactions.
6. `validate.py` checks schema, categories, yield decline and unresolved work.
7. `scrape.py` coordinates the run. Only a complete passing full run changes `latest.json`.

The downstream consumer reads `data/<store>/latest.json`, then loads its referenced immutable
products file. Failed runs stay in their own run directory. Never read a run's partial data as latest.

## Important limits

- Category discovery follows retailer category IDs, parent navigation references and child landing-page links within the main page content. Changes to
  site structure or missing child links need inspection; discovery cannot prove links Walmart hides.
- Pagination loops, missing next-page controls and zero-product listing responses stop the run.
- Unknown promotion shapes are preserved in evidence and prevent full publication.
- No CAPTCHA solving, proxy rotation, credentials, remote disabling or telemetry added by this project.
  Chrome/SeleniumBase retain their own vendor behavior; no claim is made about those dependencies.
- PPM is copied from visible listing text. Package weight comes from title or explicit package specs;
  assembled/shipping weights are not substituted for product quantity.
- A 48-hour-old checkpoint is rejected to avoid combining stale and current prices.
- Explicitly unavailable products are retained only when local pickup attribution and Walmart
  seller evidence are present. Availability evidence stays in the source sidecar to preserve the
  exact 22-field export. Missing local evidence is not inferred from a selected banner alone.
- Interrupted runs export `products.partial.json` and `failure.json` for review, without publication.
- Linux VM installation is supplied; Azure IP reputation and live retailer access are not guaranteed.

See `docs/OPERATIONS.md`, `docs/ACCEPTANCE.md` and `evidence/FINAL_REPORT.md`.

## Entry image tooling

`make_entry_image.py` is optional presentation tooling, not required by the scraper. It uses Pillow
12.3.0 and macOS Arial fonts. On Linux, change the two font paths to installed fonts.
