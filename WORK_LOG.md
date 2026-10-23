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

### Store-specific unavailable products — 07:06–07:14 UTC

- Isolated live retry succeeded for six previously unavailable items. Five had an explicit
  PICKUP option marked OUT_OF_STOCK at Bentonville S Walton Blvd Supercenter. Some remained
  available for shipping. Global availability alone is therefore insufficient.
- Added handling for the observed store-specific pickup option, verified alongside the response's
  store ID, ZIP and pickup intent. Own-seller listing candidates without pickup are now checked
  on the detail page, rather than discarded before local unavailable status can be established.
- Explicit local out-of-stock records without a local pickup offer retain empty prices, PPM and
  deal fields. Shipping prices are not copied. NOT_AVAILABLE or a different store name does not
  count as proven local out-of-stock inventory.
- Offline replay of historical listing candidates plus fresh live response captures retained two
  qualifying Office Supplies items. Three unrelated category items stayed excluded. This is
  captured-response replay, not an end-to-end fresh listing run. Additional synthetic checks pass.
- Started a fresh final-code full run at 07:10:51 UTC with no other scraper browser active. Its code
  and configuration signature is 0a08a06154f867e5f1ab9964e8e10bd39949562e39545e8bb8a6c6e9737ca599.

### Resource stop and completed visible checks — 07:18–07:30 UTC

- Current core completed 57 accepted records, including three genuine local unavailable records,
  in 458.78 seconds. Eleven parent pages completed; 1,036 pages remained pending. All 57 accepted
  records replayed without source mismatches. No publication occurred.
- The review disk guard stopped the run at 2.888 GiB free. A later read showed about 0.36 GiB,
  with system swap near 18 GiB. Project data/evidence/Git occupied about 470 MiB. No scraper or
  owned guest Chrome process remained. Space recovered after process closure; this was runtime
  resource pressure, not proof that raw source files alone filled the disk.
- Added resource samples and a 3 GiB reserve guard for the explicitly selected review process.
- Completed 11 fresh visible-price spot checks, one seeded random record from each category of
  repeat A. All visible prices matched saved prices and response prices, with correct identity,
  store, seller and pickup. Saved screenshots, event logs and response comparison fields.
- Investigated the browser helper: evaluation returns data by value and removes completed response
  transactions. This inspection did not establish a response-handle leak.
- Tried disabling back-navigation cache using Chrome's documented tooling flag. The fresh process
  hit the disk guard at 0.578 GiB during store selection, before collection. Experiment inconclusive;
  reverted the flag. No memory fix is claimed. Reference:
  https://github.com/GoogleChrome/chrome-launcher/blob/main/docs/chrome-flags-for-tools.md
- Current core signature again matches the 57-record live run:
  0a08a06154f867e5f1ab9964e8e10bd39949562e39545e8bb8a6c6e9737ca599.
- Long live testing stopped safely. The report distinguishes completed local work from full-coverage,
  repeat-reliability, live-deal and Azure gaps. Preparing the final private archive and local walkthrough.

### Final local review packaging — 23 October 2026, 07:40 UTC

- Final offline requirements (49), browser failures (13), runner flow (7), storage interruption (4), review changes and historical 500-record replay passed. All top-level Python modules compile. These are offline checks, not Azure execution.
- Recorded actual offline terminal checks and saved-evidence explanation: `evidence/walkthrough/walkthrough.cast`, transcript and 39-second MP4. Rendered with the bundled Python/Pillow runtime after the scraper environment lacked Pillow; inspected a video frame for legibility.
- Confirmed GitHub repository remains private. Final coverage, live tests, resource/context failures, missing acceptance results and their dependencies are documented in `docs/REVIEW_STATUS.md`. Contest-holder reply remains an unsent draft.
- Preparing a checksum-verified archive and updating the existing private draft release; no contest upload, message or public release authorized or performed.

### Post-cleanup reliability work — 2026-10-23T10:09:43.031198+00:00

- User authorized fixes, rerunning tests, logs and Git pushes; no client submission or message. Repository is now public at the user's earlier request.
- Added bounded readiness checks before store selection, browser-side request abort timers, uncached product fetches, explicit parsed-page cleanup and canary ZIP verification. Six offline suites passed, including the 500-record replay and permanent rejection after a location mismatch.
- First synthetic memory experiment showed root-only BeautifulSoup decompose did not release descendant trees adequately: 6.29 MB versus 6.17 MB retained with cyclic collection disabled. Preserved the failed experiment in evidence/parse-memory-decompose-only.json. Clearing descendants first reduced retained allocations to about 24 KB; this is an offline allocation test, not proof of Chrome memory improvement. Integration pending current live runs.
- Started sequential fresh sample runs with disk/resource logs. User requested no repeated progress checks. User also asked about repeated visible browser windows; headless comparison planned after these runs.

- Initial post-cleanup live launcher failed before browser startup: resolving the virtualenv Python symlink selected the system interpreter without BeautifulSoup. Fixed launcher to retain the virtualenv path. This attempt collected no products.
- Integrated descendant cleanup after the successful isolated allocation experiment. Added optional headless configuration; running headless then visible samples sequentially, never concurrently. No claim that original retailer context mismatches are fixed.

- Headless live attempt failed at the homepage with a retailer challenge. Zero product records; no publication. Exported failure/coverage/resource evidence under evidence/post-cleanup-headless. Its zero-record audit correctly failed. Headless remains opt-in and unproven for this site; visible default retained.

### Rendered product-page trial

- Visible repeat A passed 33 records in 543.20 seconds; B failed after 21 records in 383.89 seconds. Rejected response identifies Sacramento Store 3081, ZIP 95829 and SHIPPING, despite a local Store 100 listing. Captured evidence now proves the specific wrong-context response.
- Fresh same-product fetch/navigation probe both returned Store 100: failure is intermittent, not a permanently wrong URL. No cache or session root cause established.
- Eleven minimized-attempt price/store checks passed, but all observed window states were normal: minimizing did not keep Chrome hidden. Headless remains blocked.
- Trial change: product details and canaries use fully loaded browser pages, matching the route used in successful visible-price checks. Every mismatch still invalidates the run; no fallback accepts or conceals rejected data. This is a hypothesis to test, not a claimed reliability fix.

### Final observed outcome

Rendered-page trial A passed 33 records in 722.26 seconds. B failed after 23 records in 643.32 seconds with a product-context mismatch (487109111). Both accepted subsets replayed successfully. Rendered navigation therefore did not resolve the intermittent context problem and was slower; reverted that trial to the committed request path. Retained verified descendant cleanup, bounded fetch cancellation, readiness checks and ZIP canary checks. Headless failed a challenge; minimizing did not remain minimized. These are recorded failed approaches, not completed fixes. No client submission or message.

### Cache hypothesis follow-up

Eight same-session requests across the two recently rejected products compared original URLs with a fresh query parameter. All returned HTTP 200, Store 100 PICKUP, ZIP 72712 and cache-status Miss. Probe did not reproduce the fault or demonstrate an improvement. No cache-busting feature added. Only an allowlist of cache/date response headers retained; browser/session state excluded. Evidence: evidence/cache-context-probe. Intermittent long-run context remains unresolved after request and rendered-page approaches both failed repeat tests. No supported permanent fix established.

### Free transport and store-reselection trials

Compared browser fetch, Playwright context.request (shared browser cookies) and curl_cffi session (guest cookies copied in memory). Official reference: https://playwright.dev/python/docs/api/class-apirequestcontext . No cookies saved or logged. Diagnostic code compare_transports.py; optional review dependencies Playwright 1.64.1 and curl_cffi 0.16.3.

Trial flag refresh_store_each_page reselects and verifies the configured store through the normal UI after a category page introduces pending products. Then checks canary before reading product details. No acceptance bypass; previous mismatch still invalidates its run. Default behavior unchanged pending repeated live evidence. Three sequential samples planned; stop trial at first failure.

Transport comparison completed: browser-fetch 21/21 correct across three fresh sessions; Playwright 0/3 and curl 0/3, each challenged on first request per session. These targeted requests omit category traversal and therefore do not establish full-flow reliability.

Store-reselection trial A passed sample validation: 33 records across all 11 parents in 1108.35 seconds. Source audit passed. Full-run validation remains incomplete, as expected for a sample. Repeats B/C pending; no reliability claim yet.

Reselection trial final result: A/B each passed 33 with source audit; C failed after 25 on Pets product 20877373221, with location mismatch. Third accepted subset replay passed. Reselection remains opt-in, not a reliability fix. Next isolated trial requests the same product path with only fulfillmentIntent=Pickup, removing tracking/classType/filter query parameters from requests while preserving original exported URLs. All identity/store checks remain required.

Chrome-profile transport comparison completed: browser fetch 21/21; Playwright and curl Chrome-profile each 0/3 (challenge responses). This does not justify replacing the production transport. Reference: https://curl-cffi.readthedocs.io/en/stable/quick_start.html . Pickup-only request-query trial started separately with store-reselection disabled, preserving original export URLs. Browser and runner offline checks passed, including original/requested URL tracing.

Pickup-only URL trial A passed: 33 records, all 11 parent categories, 562.82 active seconds; source audit passed. No full publication. Repeats still pending.

Pickup-only URL trial: A/B passed 33 each; C failed after 15 on Beauty product 1832142965 (Sacramento 3081 SHIPPING). Not a reliable fix. Network probe saved raw guest traffic only under ignored data/network-probe; BTF product endpoint contained recommendations, not a verified primary local-product source. Next isolated trial captures only retailer-issued location cookies after selector verification and restores them in memory before product requests; no fabricated cookie values or bypass of store validation.

Cookie trial initial setup failed before browser startup due to a CDP import path; corrected to the installed mycdp dependency used by SeleniumBase. Kept the setup failure log locally; not counted as live retailer evidence.

Cookie restoration offline ordering and runner checks passed. Declared mycdp 1.4.0 explicitly because the trial directly imports the CDP package already installed through SeleniumBase. Only location-cookie names are logged; values stay on the live browser object. No manual cookie values, paid services or client submissions.

Location-cookie pinning trial: A/B passed 33 each; C failed after 2 on Diapering product 38236207. Not a reliable fix. Next isolated trial uses a new dedicated non-guest profile reused across sequential runs, under ignored data/dedicated-store100-profile. No personal browser data accessed. Other trial flags disabled; all response checks unchanged. Profile files/cookies are never included in delivery.

### Finalization requested by user

Dedicated profile A passed 33, B failed after 12 on store mismatch; source audits passed for accepted subsets. User requested stopping experimentation and finalizing with the limitation stated. Removed unsuccessful production trial options by restoring browser/runner and related checks from 3699cde (retains verified parser cleanup/timeouts/readiness/ZIP safeguards). Kept versioned evidence. Browser client-state probes exposed no product through the inspected router path; SPA network probe observed an ItemById request, not subsequently validated as a solution. Raw traffic/profile remains private under data/. No claim that every possible solution was exhausted. No client submission or message.

Final offline demonstration verification: seven suites passed; all top-level Python files compile. Profile evidence, sanitized client-state result and sanitized endpoint summary included. No scraper/review browser process remains active. Raw network bodies and dedicated profile excluded.

### Quick offline follow-up — 2026-10-23T14:05:10.795962+00:00

User authorized saved ItemById inspection, small evidence-based fixes, short tests and push. No new live requests, long runs, client messages or submission.

- Saved ItemById response was HTTP 412 with challenge keys (redirectUrl/jsClientSrc/blockScript), no product/location/price payload. Sanitized evidence/itembyid-inspection.json includes endpoint/status/field names and source hash only; raw visitor identifiers and challenge scripts remain private.
- Added 412 to immediate request rejections, avoiding repeated retries of this observed challenge response. Short HTTP checks verify one attempt.
- Normalized category queue URLs by removing only povid/athbdg tracking parameters and fragments. Pagination, functional filters, repeated and blank parameters are preserved. Next-page loop comparison uses the same normalization. In the saved 1,259-entry queue, 17 aliases collapse to 1,242 entries. This is offline analysis, not improved live coverage proof.
- Short browser, URL queue, runner and review-regression checks passed; relevant Python files compile. No speculative promotion parser change: inspected ItemById supplied no qualifying product/deal data.
- Store mismatch remains unresolved. Changed source requires a fresh run; existing checkpoints stay untouched and cannot be resumed with changed code.
