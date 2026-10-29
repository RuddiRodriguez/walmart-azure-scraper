# Step-by-step local run guide

This guide runs the scraper locally with free Python and Chrome. No paid scraping service is required.

## 1. Install requirements

Install:

- Python 3.11 or newer
- Google Chrome
- Git

## 2. Download the project

```bash
git clone https://github.com/RuddiRodriguez/walmart-azure-scraper.git
cd walmart-azure-scraper
```

Use the frozen review tag:

```bash
git checkout review-20261029-final-local
```

## 3. Create the Python environment

macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 4. Check the configured store

The demonstration configuration uses:

- Store 100
- Bentonville S Walton Blvd Supercenter
- 406 S Walton Blvd, Bentonville, AR 72712
- PICKUP

Store settings are in `config/stores.json`. Required categories are in `config/categories.csv`.

## 5. Run a small review sample

This collects two valid products from every required category:

```bash
.venv/bin/python scrape.py --store 100 --sample 2 --output data
```

A Chrome window opens. The scraper selects Store 100, checks PICKUP, visits category pages and validates every accepted product.

Sample mode saves evidence but does not publish production output.

## 6. Review the result

Run folders are stored under:

```text
data/100/runs/<run-id>/
```

Important files:

- `report.json`: pass/fail result and counts
- `products.json`: accepted products
- `events.jsonl`: collection events
- `selected-store.json`: selected store evidence
- `rejected-responses.json` or `sources/rejected/`: excluded responses
- `checkpoint.sqlite`: saved progress

For a sample, confirm `sample_validation.passed` is `true` inside `report.json`.

## 7. Resume after interruption

Use exactly the same command and add `--resume`:

```bash
.venv/bin/python scrape.py --store 100 --sample 2 --output data --resume
```

Changed code, configuration, store, sample size or a checkpoint older than 48 hours requires a fresh run.

## 8. Run full coverage

After the sample passes:

```bash
.venv/bin/python scrape.py --store 100 --output data
```

Full mode publishes only when every validation and coverage check passes. Successful publication creates:

```text
data/100/latest.json
```

If `latest.json` is not updated, read the run's `report.json` or `failure.json`. Do not treat partial output as complete production data.

## 9. Safety behavior

The scraper excludes unsupported data and stops when continuing would be unsafe. Examples:

- wrong store, ZIP or fulfillment context
- wrong product identity
- repeated transport failure
- unresolved page or product work
- duplicate products
- incomplete category coverage

Unavailable eligible products remain stored with unsupported current values left blank. Previous valid observations keep their original dates.

## 10. Current proof and limitations

- [Final delivery checkpoint](CURRENT_PROGRESS.md)
- [Evidence index](../evidence/README.md)
- [Final review status](FINAL_CLIENT_REVIEW_20261029.md)
