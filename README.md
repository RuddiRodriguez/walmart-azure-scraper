# Walmart location-aware catalog scraper

## Client review — start here

- [Live progress while final coverage runs](docs/CURRENT_PROGRESS.md)
- [Final verified status](docs/FINAL_CLIENT_REVIEW_20261027.md)
- [Running instructions](docs/OPERATIONS.md)
- [Evidence index](evidence/README.md)
- [Documentation index](docs/README.md)
- [Unsent client message](docs/CLIENT_MESSAGE_DRAFT.txt)

Production collector: `scrape.py`. Supporting production modules: `browser.py`, `extract.py`, `storage.py`, `retention.py`, and `validate.py`. Tests, diagnostics and evidence helpers live under `tools/`.

Corrected plan baseline: [step 1 report](docs/CORRECTED_PLAN_BASELINE.md) and [requirement register](evidence/corrected-plan-20261025/requirements-register.json). Existing evidence is reusable only within its recorded source/configuration/scope; outstanding requirements remain open.



Python collector with local Chrome, store/category configuration, checkpoints, source evidence,
validation and atomic publication. No paid scraping APIs or proxies.

## Current review status

Two independent bounded runs each produced **506 validated distinct products across all 11 required
categories**, using identical collection-code hashes, plan bytes, configs and dependency versions.

|Measure|First run|Repeat|
|---|---:|---:|
|Accepted records|506|506|
|Rejected responses|11|6|
|Processing errors / duplicate IDs|0 / 0|0 / 0|
|Runtime seconds|2063.272|2048.379|

Repeat rejected two wrong-store responses and four without local pickup; it continued without
retrying them. Every accepted row independently passed source/store/Pickup/price checks.
468 IDs overlap; all 433 comparable nonblank effective prices match. One common product became
locally unavailable and its current local price remains blank. Each sample retained 35 unavailable
products. Sample-only IDs are not proof of new/deleted products.

- [Repeat actual JSON](evidence/controlled-skip-invalid-repeat-20261025/products.json)
- [First actual JSON](evidence/controlled-skip-invalid-20261025/products.json)
- [Comparison](evidence/controlled-skip-invalid-repeat-20261025/COMPARISON.md)
- [Repeat source/hash audit](evidence/controlled-skip-invalid-repeat-20261025/summary.json)
- [Run/audit instructions](docs/CONTROLLED_COLLECTION.md)
- [Review status and remaining gaps](docs/REVIEW_STATUS.md)

Producer source commits:e90c5f0 (first),2ff5e20 (repeat); commit IDs differ as evidence/docs advanced,
while producer bytes match. Raw bodies/native DOM/private pair originals remain local; safe review
JSON/audits are public. No upstream store-drift remedy claimed.

This proves bounded-sample repetition, **not full uncapped category coverage/repeated full catalog**.
Current-wrapper recovery passed a separate three-product live SIGKILL/resume test at 45ba7c4;
see [step8 results](evidence/step8-controlled-recovery-20261026/RESULTS.md). Full-catalog recovery remains unproven.
Offers and Azure remain open. Privacy-reviewed wrong/correct sharing copies are included under
`evidence/response-pairs-reviewed-20261026/`; complete originals remain private and hash-recorded. Earlier
samples/failed runs stay separate; earlier frozen ZIPs are historical. Nothing sent/submitted to client.

## Latest client review package

Version: `review-20261027-client-ready-v2`.
[Download source and review evidence](https://github.com/RuddiRodriguez/walmart-azure-scraper/archive/refs/tags/review-20261027-client-ready-v2.zip).
[Final status](docs/FINAL_CLIENT_REVIEW_20261027.md); [verification](docs/VERIFY_PACKAGE.md); [unsent client message](docs/CLIENT_MESSAGE_DRAFT.txt).

Package includes reviewed response pairs, retention trace, two 506-product runs, 506-product interruption/resume proof, current-collector recovery and repeat proof, bounded category reconciliation, and zero-result genuine-offer evidence. Full category coverage and qualifying offer examples remain unproven. Azure remains separate.

## Retention update after client feedback

[Step2 trace and results](evidence/retention-step2-20261026/README.md): eligible products now remain
recorded without a current pickup offer or verified price; unsupported values blank, original dated
history kept without expiry. Unproven assortment stays separate. [Retention behavior](docs/RETENTION.md).
Current retention implementation4a68607 has offline real-capture replay and caller tests, not new
large live/recovery proof. Earlier frozen package/source claims keep their recorded scope.

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

Runtime scraper files stay at the repository root. Tests, diagnostics, evidence builders and
review helpers live under `tools/` and run with `python -m tools.<name>`. Keep this split when
adding new files: production collection logic belongs at the root; supporting utilities belong
under `tools/`.

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

`tools/make_entry_image.py` is optional presentation tooling, not required by the scraper. It uses Pillow
12.3.0 and macOS Arial fonts. On Linux, change the two font paths to installed fonts.

## Local review commands

These checks are offline unless explicitly marked live:

```bash
python -m tools.check_page_urls
python -m tools.check_package_audit
python -m tools.check_requirements
python -m tools.check_review_changes
python -m tools.check_storage_recovery
python -m tools.check_runner_flow
python -m tools.report_local_runs
python -m tools.export_run_evidence data/<output>/<store>/runs/<run-id> evidence/<review-name>
python -m tools.audit_run evidence/<review-name>
python -m tools.compare_runs evidence/<first> evidence/<second> evidence/repeat-comparison.json
```

The exporter includes page and candidate states, rejection reasons, skipped-link decisions, source
responses and HTML hashes. Full HTML and browser/session state stay local under `data/`. A stopped
run exports partial products; it does not replace `latest.json`. Offline tests using constructed
offers or simulated navigation are labeled explicitly in their JSON reports.

`tools/hard_stop_review.py` intentionally kills an explicitly selected scraper process for recovery
testing. It needs `requirements-review.txt`; use only on a disposable review run.
`tools/verify_hard_recovery.py` checks the later live continuation against the captured committed state.
After a hard kill, `active_time_complete=false` indicates missing active-runtime accounting; use
elapsed time with its interruption caveat.

`tools/spot_check.py` is live: it opens a fresh browser, selects the configured store, and compares one
randomly chosen record per represented category against visible product-page prices.
`tools/probe_unavailable.py` is a bounded live investigation of previously observed unavailable items.
Neither is a full catalog acceptance run.

`tools/record_walkthrough.py` records actual offline command output to an asciicast and text transcript.
`tools/render_walkthrough.py` optionally renders that recording with Pillow, ffmpeg and a supplied font.
The video is a local review walkthrough, not footage of an Azure deployment or a full live crawl.

### Browser visibility and memory checks

The collector reuses one Chrome window within each run. Separate runs start fresh sessions.
Set `"headless": true` in the store configuration to request Chrome without a visible window;
omit it or use `false` for a visible window. Verify retailer access in the selected mode before
unattended use. Headless mode alone is not a memory guarantee.

`python -m tools.check_parse_memory` compares synthetic HTML parsing allocations with and without
explicit descendant cleanup. It does not measure Chrome or prove long-run resource stability.
Product fetches now have browser-side cancellation timers as well as Python timeouts,
and store canaries check ZIP in addition to store ID and pickup context.

### Short store-context diagnostic (live)

`trace_store_context.py` opens one fresh guest browser and checks a control and the previously
failed product before and after each explicitly named parent category. It scrolls twice per visit.
Default: one category, five product fetches including one immediate repeat. With three categories:
eight fetches, checking the same two products to isolate category changes. Both modes stop after
180 seconds or the first failure.
It does not crawl children, publish products, reset cookies or relax store checks.
Use a new private output folder for each run:

```bash
python trace_store_context.py --failure evidence/profile-b/failure.json --output data/context-trace-new
```

The JSON log compares visible store banners, product-response store/ZIP/intent and changes in three
named location cookies. Cookie values remain in memory only. Raw HTML stays in the private output
folder. A matching response verifies location context only, not seller, availability or price.
See `evidence/store-context-trace-short/` for the bounded result and its limitations.

To check a short category-switch sequence without child traversal:

```bash
python trace_store_context.py --categories Diapering Beauty "Personal Care" --output data/context-switches-new
```

`evidence/store-context-switches-short/` records a 112.99-second, three-category diagnostic.
Eight responses matched Store 100 pickup; this does not establish complete or repeated reliability.

### Optional store diagnosis

Set `"trace_store_context": true` in a separate review configuration to log the visible store banner
and location-cookie names/change flags before product requests and after a rejected response.
Cookie values stay in memory. Diagnostic capture failure cannot hide the original validation
error. Product response logs include status, final URL without query values, redirect flag and
an allowlist of cache/date headers. These observations do not establish the cause of store drift.
Start a fresh run after code/configuration changes.

`tools/probe_collection_context.py` is review-only: on a location rejection it records immediate visible
store state, makes at most one same-page re-fetch and one visible navigation, then re-raises the
original rejection. A probe never repairs or publishes the failed run. Stop after a challenge.
Use a fresh private output folder and the same normal collection configuration.

`tools/guard_review_disk.py` accepts `--stop-at 2026-10-24T14:36:31+00:00` to enforce a review cutoff
with SIGINT. It targets only the selected collector PID and also retains its disk-reserve check.

Primary listing pagination supports ordinary hrefs and observed JavaScript controls carrying an
explicit sequential paginationPage. Query filters are retained. Wrong explicit primary-listing
store metadata stops collection. Embedded landing-page recommendation/shelf widgets are not
accepted as primary local catalog data merely because the visible banner matches.
