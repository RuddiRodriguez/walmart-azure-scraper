# Local acceptance review — 23 October 2026

The package contains usable source and genuine collection evidence. It is not yet proven reliable
for complete unattended collection or Azure production. All live scraper processes have stopped.
Nothing has been submitted or messaged to the contest holder during this review.

## Final demonstration decision

User requested ending further experiments and finalizing the reviewable portion. No client submission or message performed.

Latest dedicated-profile trial: A passed 33 products; B stopped after 12 products because the product response changed store context. Both accepted subsets passed source audits. No failed run published production data.

Additional free trials also failed repeated reliability checks:

| Approach | Observed result |
|---|---|
| Playwright shared-cookie requests | Challenges in all six sessions across two comparisons |
| curl sessions, including Chrome compatibility | Challenges in all six sessions |
| Browser targeted-request diagnostics | 42/42 passed, but omitted category traversal |
| Store reselection after category navigation | 33 passed, 33 passed, then mismatch after 25 |
| Pickup-only product request query | 33 passed, 33 passed, then mismatch after 15 |
| Restoring retailer-issued location cookies | 33 passed, 33 passed, then mismatch after 2 |
| Dedicated reusable browser profile | 33 passed, then mismatch after 12 |

The main collector retains the previously verified memory cleanup, request cancellation, readiness and ZIP checks. Failed experimental options were removed. Their code remains in versioned history (notably 1e017bf, 5554bb8, 4580879 and 5f7ff19). New client-state and network observations are exploratory only, not validated fixes. Raw network responses and browser profiles remain excluded from Git and delivery.

This package is a working demonstration with a documented reliability limitation. It is not ready to claim full unattended production acceptance. Historical 500-product JSON remains included; these repeat samples are not a new complete catalog run. No full completion time can be promised from the available results.

## Latest follow-up results

A later eight-request cache probe on both recently rejected product URLs returned correct Store 100 pickup context with both original and fresh-query URLs. Every response reported cache-status Miss. This did not reproduce the fault or justify a cache-busting fix; evidence is under `evidence/cache-context-probe`.


Post-cleanup request-path sample A passed 33 records (543.20 seconds); B failed after 21 records (383.89 seconds) with Sacramento Store 3081 SHIPPING data. Both accepted datasets passed source replay. A fresh exact-product probe returned correct Store 100 context through both fetch and navigation: the cause remains intermittent and unproven.

A fully loaded page trial passed 33 records once (722.26 seconds), then failed after 23 (643.32 seconds) on another location mismatch. That trial was reverted. No passing repeated-run claim.

Parser cleanup reduced retained allocations in an isolated synthetic check from about 6.3 MB to 24 KB. Live request runs peaked at 171–173 MB Python RSS and 1,959–2,090 MB browser-child RSS. This does not establish long-run memory stability. Browser requests now cancel on timeout; store selection waits for controls; canaries verify ZIP.

Headless Chrome hit a retailer challenge. Eleven minimize-attempt price checks passed, but Chrome window state returned to normal; hidden-window operation on this Mac remains unresolved. Linux Xvfb is supplied but untested on Azure.

Repository is public by user request. The historical package and walkthrough predate these follow-up tests; latest evidence folders and this report take precedence.

## What we have

| Requirement | Evidence and boundary |
|---|---|
| 500 genuine distinct products | `evidence/products-500.json` and corresponding source records. Historical live collection, rechecked offline; all 11 parent categories represented. This is not a new complete catalog run. |
| Broader live collection | Intermediate attempt reached 259 accepted records and 27 completed pages. `evidence/full-attempt-v3-final/` preserves its partial data, sources and queue. |
| Latest collector live check | `evidence/final-local/`: 57 accepted records, 11 completed parent pages, 458.78 seconds. It stopped at the disk reserve; 1,036 pages remain pending. No full publication. |
| Correct store and fulfillment | DOM name/address, response Store 100, ZIP 72712, pickup intent and local fulfillment checked. Screenshots show Bentonville S Walton Blvd Supercenter, 406 S Walton Blvd. Store 100 is still a trial location, not confirmed client assignment. |
| Independent visible price checks | `evidence/visible-price-check/`: 11 fresh product pages, one randomly selected record per represented category. All visible prices matched the saved record and structured response; store, seller and pickup checks passed. |
| Unavailable-product retention | `evidence/unavailable-fresh/`: three genuine records from fresh listing-to-detail collection. Explicit local OUT_OF_STOCK evidence is retained; shipping prices/PPM are not copied. All three replayed correctly. |
| Exact schema and data checks | Ordered 22 string fields; missing values empty; UPC preserved; GUPC and unit_price empty; PPM copied, not calculated. Offline audits passed for the historical 500 and each exported accepted dataset. |
| Duplicate and exclusion controls | Product IDs deduplicated before detail collection. Sponsored, marketplace, outside-category and approximate-weight exclusions recorded. Own-seller candidates without a pickup summary require detail verification; they are not automatically accepted as local. |
| Abrupt recovery | Live page-stage SIGKILL preserved four prior page commits. Live product-stage SIGKILL preserved six records; the interrupted request was retried and committed once. `evidence/hard-page-recovery/` and `evidence/hard-product-recovery/`. |
| Failed-run protection | Live incomplete/failed runs did not publish. Offline tests verify prior-output preservation, atomic success, transaction rollback, same-job overlap rejection and permanent publication blocking after a location mismatch. |
| Source and operations | Unencrypted Python source, pinned runtime requirements, captured local dependency versions, configuration, recovery/extension instructions and existing-VM installation/timer files supplied. |

Counts from different runs overlap. Do not add them together as a unique-product total.

## What is missing, and why

| Missing acceptance result | Exact reason and next dependency |
|---|---|
| Complete category/subcategory exhaustion | Not observed. Latest tested run has 1,036 pending pages; earlier broader attempt had 1,232 pending. Queues are separate snapshots, not counts to combine. Every available category cannot be claimed from parent representation. |
| Consistently successful unattended repeats | Repeat A completed 33 records in 552.93 seconds. Repeat B failed after seven records with a location mismatch; its event span was about 340 seconds. `evidence/repeat-comparison.json` records seven common IDs and no price changes among those IDs. The second run is a failure, not a passing repeat. |
| Stable fulfillment over a long run | Two earlier attempts received mismatched location context. One exact product worked in a fresh session, but the cause was not established. The original rejected responses predated pre-validation capture and are not available; new capture behavior is verified offline. No claim that the retailer/context issue is permanently fixed. |
| Long-run resource stability on this Mac | A 3 GiB reserve stopped the latest crawl at 2.888 GiB free. Free space later fell to roughly 0.36 GiB, then recovered after process closure. A fresh browser experiment tripped at 0.578 GiB. The project's saved files were about 470 MiB; system swap was substantial. Root cause remains unproven. The attempted back-navigation-cache setting was reverted after an inconclusive test. More storage/memory headroom or a measured resource fix is needed before another long run. |
| Genuine volume/digital deal demonstrations | No qualifying live examples verified. Ordinary sales exist. Synthetic examples cover the specified wording and no-invented-price rules; unknown local promotion shapes block full publication. Do not label synthetic offers as live. |
| Azure execution and scheduling proof | Not run. Client VM address, OS/configuration and approved access path were not supplied. Local acceptance also remains incomplete. Azure stays last, as requested. Installer syntax was checked; that is not Linux/Azure runtime evidence. |
| Assigned location and previous private feedback | The supplied brief/reminder are available. Store assignment and a complete previous private-feedback thread are not. These cannot be assumed resolved. |

## Changes completed

- Check product details after each listing page, spread work across categories, prioritize pagination
  and listings, and preserve landing pages in the queue.
- Log page/product starts, retries, exact failures, candidate outcomes and skipped-link reasons.
- Check actual response ZIP and scraped store name/address against the configuration.
- Retain verified local unavailable items while omitting unverified shipping prices and offers.
- Save product responses before validation and preserve rejected responses separately.
- Permanently bar a location-mismatched run from publication, even after a later resume. Use a fresh
  run for publication; do not relax this check to obtain a passing result.
- Reject malformed schema, duplicate IDs, inconsistent dates/prices and unresolved detail reviews.
- Keep code/configuration signatures in both modes. Mark runtime incomplete after an unclean kill.
- Add reproducible offline checks, live recovery evidence, source audits, resource logging and a
  review disk guard. The guard intentionally stops only the explicitly selected review process.

## Test labels

`check_requirements.py` has 49 named offline checks. `check_browser_failures.py` has 13 offline
HTTP/timeout/shape/canary checks. `check_review_changes.py`, `check_storage_recovery.py` and
`check_runner_flow.py` cover unavailable cases, prior publication, transaction kills and runner flow.
Their JSON reports explicitly identify simulated data/navigation. Offline success is not live or
Azure acceptance. The recorded walkthrough demonstrates local checks and saved evidence only.

## Reproduce and continue

See `README.md` and `docs/OPERATIONS.md`. Install Chrome and the pinned Python requirements.
The earlier tested core matched run signature
`0a08a06154f867e5f1ab9964e8e10bd39949562e39545e8bb8a6c6e9737ca599`.

The following earlier checkpoint requires its original code; current code must start a fresh run:

```bash
python scrape.py --store 100 --output data/final-local-20261023 --resume
```

Use the exact same code and configuration. This checkpoint stopped for disk pressure and has no
recorded location mismatch. Older code checkpoints must not be migrated silently. For a new run,
omit `--resume`. Do not resume a location-mismatched run expecting it to publish.

The raw HTML/checkpoints remain local under `data/`; the private package contains selected source
responses, screenshots, hashes, logs and explicit coverage states. No browser/session state is
included in the delivery archive.

## Completion timing

The completed local portion is reviewable now. No defensible full-acceptance completion date can
be given while long-run resource stability, fulfillment consistency, assigned-store confirmation
and Azure access remain unresolved. A dated estimate must follow those prerequisites and a timed
complete run; promising completion before the contest closes would not be supported by these results.
The previously saved deadline is 24 October 2026, 16:03:08 UTC / 18:03:08 CEST; check the live contest
countdown before any eventual submission. No submission is authorized by this review.
