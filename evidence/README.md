# Evidence index

## Current client evidence

Current local summary: [`docs/CLIENT_STATUS_20261104.md`](../docs/CLIENT_STATUS_20261104.md).

| Requirement | Evidence |
|---|---|
| Current checkpoint and verification | `docs/CLIENT_STATUS_20261104.md`, `docs/VERIFY_PACKAGE.md` |
| Run source and configuration | `final-package-20261101/RUN_PROVENANCE.json` |
| Full file manifest | `SHA256SUMS.json` |
| Wrong-store and corrected-response pairs | `response-pairs-reviewed-20261026/` |
| Unavailable-product retention | `retention-step2-20261026/` |
| 506-product interruption and resume | `point3-20261026/recovery-506/`, `point3-20261026/recovery-reevaluation.json` |
| Separate 506-product repeat | `point3-20261026/repeat-506/` |
| Current collector correctness | `phase-a-live-20261027/` |
| Current cached repeat | `phase-b-live-20261027/` |
| Category reconciliation | `phase-c-bounded-200-20261027/` |
| Genuine-offer search | `phase-d-offers-20261027/` |
| Current collector interruption/resume | `phase-e-recovery-20261027/` |
| Current collector repeat comparison | `phase-e-repeat-20261027/` |
| Expanded genuine-offer review | `expanded-offers-20261028/` |
| Two bounded Azure diagnostics and historical cleanup record | `azure-sequence-20261027/` |
| Corrected provider usage and one future-test limit | `transport-correction-20261031/` |
| Full offline regression | `full-offline-regression-20261031/` |
| Latest coverage ledger and completed batches | `point3-coverage-queue-20261026/` |
| Coverage failure classification | `coverage-failure-ledger-20261030/` |
| Publication, retry and fresh-yield safeguards | `client-review-20261029-safeguards/` |
| Package-size behavior | `package-size-checks-20261030.json` |
| Oxylabs residential test | `oxylabs-bounded-20261030/` |
| Oxylabs Web Unblocker test | `web-unblocker-bounded-20261030/` |
| Scrape.do Store 100 test | `scrapedo-bounded-20261030/` |
| Scrape.do exact-endpoint support request | `scrapedo-support-20261101/RESULT.json` |
| Scrape.do three-request Store 100 result | `scrapedo-store-controls-20261104/RESULT.json` |
| Scrape.do privacy-reviewed source excerpts | `scrapedo-store-controls-20261104/source-excerpts/MANIFEST.json` |
| Scrape.do exact November 4 run producer | `scrapedo-store-controls-20261104/PRODUCER_PROVENANCE.json` |
| Listing-runner offline safeguards | `scrapedo-listing-runner-20261106/OFFLINE_TESTS.json` |
| Updated full offline regression | `full-offline-regression-20261104/RESULT.json` |
| Bright Data Store 100 test | `brightdata-bounded-20261030/` |
| Store-session recovery result | `store-session-recovery-20261030/RESULT.json` |

Evidence folders contain review-safe exports and their own hashes where applicable.

## Historical annex

Older 500-product demonstrations, 33-product samples, failed runs, transport experiments, screenshots and previous frozen packages remain in this folder for audit history. They must not be combined with current result counts.

## Private evidence

Full HTML responses, browser profiles, cookies, session state and unredacted captures remain outside Git under ignored local `data/` storage. Public evidence contains reviewed fields, hashes and redacted copies only.

## Open limits

- Full category and pagination coverage remains incomplete.
- The four Walmart volume/digital fields must remain empty by client instruction. No further offer search is required.
- Corrected re-fetch evidence does not prove one retry prevents future store drift.
- Two bounded Azure diagnostics completed. The Store 100/PICKUP control passed in two regions, but the following Art Sets listing was blocked in both. Signed-in Azure Portal filters verified both temporary resource groups are absent.
- The three Scrape.do product controls preserved Store 100, ZIP 72712, product identity,
  displayed price and PICKUP status. The pumpkin was OUT_OF_STOCK, and the source did not
  provide a fulfillment-specific price. Category/listing transport and the full paid run remain
  unapproved and incomplete.

No client message or contest submission is performed by repository tooling.
