# Work log

## 2026-10-23 review package

Requested scope: prepare the latest reviewable package, log and push every change privately.
Do not submit, upload or message the contest holder.

- Read the original DOCX, category CSV, current contest overview and own entry #69.
- Fresh overview countdown: 1 day, 13 hours remaining at approximately 02:37 UTC.
  The older saved contest metadata gives October 24, 2026 at 16:03:08 UTC / 18:03:08
  Europe/Amsterdam (CEST). Treat the live platform countdown as authoritative.
- No comments were visible beneath entry #69. Earlier private feedback was not available in the
  supplied project files. The reminder and published brief are the audited inputs.
- Re-audited all 500 historical records against their captured listing and product evidence:
  no duplicate IDs/URLs, store/seller/price/UPC/PPM checks passed. This is an offline audit.
- Added the original multi-pass collection logs and original requirements to the private package.
- Changed unavailable-product handling: retain explicitly unavailable records when seller and
  local pickup evidence remain present. Preserve missing prices as empty strings only for those
  records. Do not infer a local offer when pickup evidence is missing.
- Added partial JSON and failure metadata export on interrupted/failed runs. Production pointer
  remains untouched.
- Offline synthetic checks cover unavailable products with/without prices, wrong-store rejection,
  missing-price validation and checkpoint close/reopen. These are not live acceptance results.
- Started a fresh 3-per-category live sample; results recorded separately under evidence/review-live.

### Outstanding acceptance work

Full subcategory traversal, complete repeated catalog runs, genuine observed unavailable-item
retention, live volume/digital offers, product-stage interrupted live recovery and Azure execution
remain subject to observed results. Store 100 is still a trial store, not confirmed client assignment.
No Azure VM address, approved login path or client environment has been supplied; no Azure resources
or paid services were created. No completion date for external acceptance can be guaranteed without
those prerequisites.

### Subsequent review steps

- Commit `3b87f48` pushed privately: parser/validation/failure changes and historical evidence audit.
- Commit `3c9b31b` pushed privately: review status, unsent reply, evidence exporter and interruption tool.
- Added an offline simulated access-block check: previous publication stayed byte-identical;
  empty partial output and failure metadata were saved. Results are in review-regression.json.
- Original data's record timestamps span October 22, 2026, 23:19:42–23:27:39 UTC. This timestamp
  range is not the total collection runtime.
- Saved the fresh contest countdown screenshot. Public clarification board and older comments
  do not establish an assigned store or provide an Azure access path.
- Fresh run intentionally interrupted at 02:40:48 UTC, after three committed products and 20
  completed listing/category pages. This occurred between product requests, not mid-response.
  Resumed with the identical store, sample size, configuration and parser/runner code.

### Completed local review

- Fresh sample finished at 02:43:28 UTC / 04:43:28 CEST: 33 records, three per parent category.
  Sample validation passed. Zero duplicate IDs/URLs, 33 UPCs, 26 displayed PPM values.
- Live graceful-interruption recovery passed: three prior records retained and processed once,
  and all 20 prior page completions recorded once. No full-run publication occurred.
- Exported selected source responses, event log, queue coverage, local HTML hashes, environment,
  partial failure evidence and recovery report into `evidence/review-live/`.
- Outstanding: 1,094 queued pages, 290 candidates, genuine unavailable/deal cases, repeated full
  runs and Azure acceptance. Live retained-unavailable count is zero, so this remains unproven.
- Updated the review matrix and unsent reply with actual fresh-run results. Original 500-record
  JSON remains unchanged and separately identified as historical live collection.
- Refreshed the top-level README/acceptance summary and regenerated package checksums. Delivery
  archive is built from the committed tree, verified against the checksum manifest and stored as
  a draft release in the existing private repository. This is not a contest upload or client message.

## Expanded local acceptance work — October 23, 06:17 UTC onward

- Started an unrestricted full-mode crawl on revision af0ca01. Killed the process with SIGKILL
  immediately after a Diapering page load. Four earlier completed pages survived; SQLite integrity
  was `ok`. Resumed unchanged code: completed pages were not repeated; the interrupted page loaded
  again and completed exactly once. Evidence: `evidence/hard-page-recovery/`.
- Stopped that baseline deliberately after proving recovery, to fix issues found in code review.
  This was not an access-block failure or a completed full crawl. Eight pages completed, zero
  product details collected because the old runner postponed all product checks until the end.
- Revised the runner to check products after each page, alternate pending work across categories,
  and base sample completion on accepted records rather than unverified candidate count.
- Added page/product start events, explicit failure URLs, listing rejection evidence, skipped-link
  reasons, detail retry logs and code/config signatures in both full and sample modes.
- Prevented publication when detail prices, availability or promotions need review. Failed sample
  validation now produces a failing exit code. ZIP is taken from the retailer response and checked.
- Hardened schema checks against malformed records; added duplicate product ID, date and address
  checks. Added 48 passing offline checks, explicitly synthetic where fields/offers are mutated.
- Code now marks active runtime as incomplete after an abrupt unclean stop; elapsed wall time
  remains available. Missing runtime from a killed process is not silently called complete.
- Started a fresh revised full-mode crawl at 06:26 UTC. Product-stage SIGKILL test is queued.

### Recovery and parser review — 06:33 UTC

- First product-stage SIGKILL fired between requests after three commits; it is logged as such.
  Fixed the test watcher to require the latest event to be a newly started product request.
- Second SIGKILL happened after request start for product 15154970737, before its record committed.
  Six prior records survived. Resume retried that product once, completed it once, preserved all
  prior pages/products without repeats, and passed SQLite integrity checks. Exact network-packet
  timing was not measured. Evidence: `evidence/hard-product-recovery/hard-recovery.json`.
- An overlap-test attempt raced with the first kill and started a new run after the lock had been
  released. Stopped that test run during store selection, restored the known checkpoint pointer,
  and repeated the overlap check while the resumed process actually held the lock: correctly
  rejected. Both the failed test setup and passing result are retained, not hidden.
- Offline transaction SIGKILL test passed: prior data retained, uncommitted writes discarded,
  and a subsequent transaction succeeded. `evidence/storage-crash-check.json`.
- Inspected 2,129 genuine historical listing observations. All 28 unavailable observations lacked
  explicit Store 100 pickup evidence. These cannot establish live local unavailable-item retention.
- Found and fixed combined-category-ID handling introduced by the first ancestry restriction.
  Added its regression test. Total requirement checks now 49, all passing offline.
- Revised page selection to take one pending page per category per round and prioritize next-page
  URLs. This avoids processing an entire large child queue before continuing pagination.
- Store name/address are now read from retailer DOM strings and checked against configuration;
  ZIP comes from each product's retailer response. Saved store metadata documents this source.
- Deliberately ended the intermediate v2 run after 26 valid records to use these fixes. Offline
  replay matched all 26 exported records. Started the fresh v3 full run at 06:33:26 UTC.

### Additional checks and repeat plan — 06:42 UTC

- Offline runner integration passed: simulated two-page navigation, duplicate removal, successful
  full-mode publication, committed-product resume and cross-mode checkpoint rejection. This used
  captured product data with simulated navigation; it is not a completed live full run.
- Captured the installed local runtime and 57 runtime dependency versions. Ubuntu installer shell
  syntax passed locally. Azure CLI, Docker and systemd validation are not available on this Mac;
  no Linux/Azure runtime result is claimed.
- Added a complete local checkpoint register, repeat-run comparison tool and terminal walkthrough
  recorder/renderer. Walkthrough tools only run local checks and show saved evidence.
- Began a fresh 3-per-category repeat sample while the full crawl continues. Repeat-sample timing
  will therefore include shared-machine/network load and must not be called an isolated benchmark.

### First broader live failure and investigation — 06:49–06:53 UTC

- Full v3 collection stopped at 143 accepted products when product 5116082136 returned a location
  mismatch. This prevented publication. Exported and replay-audited all 143 accepted records;
  zero source mismatches. The queue contained 1,138 discovered/completed URLs at this snapshot.
- The original failed product response was not written before validation raised; this is an
  evidence-capture weakness to fix. Do not claim its exact rejected location is preserved.
- A fresh, separate session checked that exact URL both through fetch and visible navigation.
  Both returned Store 100/PICKUP, correct ZIP, IN_STOCK. Screenshot also shows Bentonville pickup.
  This demonstrates recovery in a fresh session, not a diagnosed or permanently fixed root cause.
- Resumed the unchanged full run at 06:52:37 UTC. The failed product then passed and collection
  continued. The run is interrupted/resumed, not an uninterrupted production benchmark.
- Repeat A completed 33 valid records across all 11 parents; all 33 matched exported source on
  offline replay. Repeat B began with the same code/configuration/sample size at 06:52:37 UTC.
- The first extra unavailable-item probe failed before store selection (pickup banner not found).
  No product was collected in that attempt. A later isolated retry will preserve diagnostic images.

### Repeat failure and stricter publication protection — 07:05 UTC

- Repeat B failed after seven accepted records, on product 47376050, with another location mismatch.
  Repeat A passed (33 records, 552.93 seconds); B's event span was about 340 seconds before failure.
  Seven common records had unchanged prices, but the incomplete second run is not a successful
  reliability test. `evidence/repeat-comparison.json` preserves this distinction.
- Stopped the resumed v3 full attempt deliberately to improve failure capture and publication
  guarantees. It had 259 valid records and 1,259 discovered/completed URLs. All 259 passed offline
  source replay. It is a partial, interrupted run and cannot establish full catalog coverage.
- Added pre-validation product source capture and separate immutable rejected-response files.
  A later retry cannot overwrite the rejected response evidence.
- A location mismatch now permanently bars that run from publication, including after resume.
  A fresh clean run is required. Offline integration verifies this and saved rejected-response data.
- Full traversal now prioritizes actual listing pages and pagination across categories, while
  retaining landing pages in the queue, to reach useful category breadth sooner.
- Added 13 passing offline HTTP/timeout/malformed-response/canary checks. They are not live block
  demonstrations. Retrying the unavailable-item investigation with no other scraper browser active.
