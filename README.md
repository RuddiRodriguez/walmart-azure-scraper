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
Latest local review: a broader attempt produced 259 valid partial records. An earlier core
collected 57 records, including three genuinely unavailable local items, before the disk reserve
stopped it. Eleven fresh visible-price checks passed. One 33-record repeat passed and another
failed on a location mismatch. Live hard-kill recovery passed at page and product stages.

Read `docs/REVIEW_STATUS.md` for the exact evidence and unresolved requirements. Full catalog
coverage, consistent unattended runs, genuine volume/digital deal demonstrations and Azure
execution remain unproven. Nothing was submitted to the contest holder during this review.

## Local setup

Install Chrome and Python 3.11+. macOS or Linux supported; Windows requires adapting the file lock.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scrape.py --store 100 --sample 2
```

Sample mode checks products after each listing page and continues discovery until the requested
number of accepted records is reached in each category or the available queue is exhausted.
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
- Unknown local promotion shapes are preserved in evidence and prevent full publication.
- A location mismatch permanently bars that run from publication, including after resume. Start a fresh run.
- No CAPTCHA solving, proxy rotation, credentials, remote disabling or telemetry added by this project.
  Chrome/SeleniumBase retain their own vendor behavior; no claim is made about those dependencies.
- PPM is copied from visible listing text. Package weight comes from title or explicit package specs;
  assembled/shipping weights are not substituted for product quantity.
- Changed code/configuration cannot resume either a full or sample checkpoint. A 48-hour-old checkpoint is rejected to avoid combining stale and current prices.
- Explicitly unavailable products are retained only when local pickup attribution and Walmart
  seller evidence are present. An explicit pickup OUT_OF_STOCK option for the verified store also
  establishes unavailable local inventory; shipping prices and PPM stay empty. Availability evidence stays in the source sidecar to preserve the
  exact 22-field export. Missing local evidence is not inferred from a selected banner alone.
- Interrupted runs export `products.partial.json` and `failure.json` for review, without publication.
- Linux VM installation is supplied; Azure IP reputation and live retailer access are not guaranteed.

See `docs/OPERATIONS.md`, `docs/ACCEPTANCE.md` and `evidence/FINAL_REPORT.md`.

## Entry image tooling

`make_entry_image.py` is optional presentation tooling, not required by the scraper. It uses Pillow
12.3.0 and macOS Arial fonts. On Linux, change the two font paths to installed fonts.

## Local review commands

These checks are offline unless explicitly marked live:

```bash
python check_requirements.py
python check_review_changes.py
python check_storage_recovery.py
python check_runner_flow.py
python report_local_runs.py
python export_run_evidence.py data/<output>/<store>/runs/<run-id> evidence/<review-name>
python audit_run.py evidence/<review-name>
python compare_runs.py evidence/<first> evidence/<second> evidence/repeat-comparison.json
```

The exporter includes page and candidate states, rejection reasons, skipped-link decisions, source
responses and HTML hashes. Full HTML and browser/session state stay local under `data/`. A stopped
run exports partial products; it does not replace `latest.json`. Offline tests using constructed
offers or simulated navigation are labeled explicitly in their JSON reports.

`hard_stop_review.py` intentionally kills an explicitly selected scraper process for recovery
testing. It needs `requirements-review.txt`; use only on a disposable review run.
`verify_hard_recovery.py` checks the later live continuation against the captured committed state.
After a hard kill, `active_time_complete=false` indicates missing active-runtime accounting; use
elapsed time with its interruption caveat.

`spot_check.py` is live: it opens a fresh browser, selects the configured store, and compares one
randomly chosen record per represented category against visible product-page prices.
`probe_unavailable.py` is a bounded live investigation of previously observed unavailable items.
Neither is a full catalog acceptance run.

`record_walkthrough.py` records actual offline command output to an asciicast and text transcript.
`render_walkthrough.py` optionally renders that recording with Pillow, ffmpeg and a supplied font.
The video is a local review walkthrough, not footage of an Azure deployment or a full live crawl.

### Browser visibility and memory checks

The collector reuses one Chrome window within each run. Separate runs start fresh sessions.
Set `"headless": true` in the store configuration to request Chrome without a visible window;
omit it or use `false` for a visible window. Verify retailer access in the selected mode before
unattended use. Headless mode alone is not a memory guarantee.

`python check_parse_memory.py` compares synthetic HTML parsing allocations with and without
explicit descendant cleanup. It does not measure Chrome or prove long-run resource stability.
Product fetches now have browser-side cancellation timers as well as Python timeouts,
and store canaries check ZIP in addition to store ID and pickup context.
