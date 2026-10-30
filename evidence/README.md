# Evidence index

## Current client evidence

Final local summary: [`docs/CURRENT_PROGRESS.md`](../docs/CURRENT_PROGRESS.md).

| Requirement | Evidence |
|---|---|
| Final status and package receipt | `docs/FINAL_CLIENT_REVIEW_20261029.md`, [`client-final-20261029/receipt.json`](https://github.com/RuddiRodriguez/walmart-azure-scraper/blob/main/evidence/client-final-20261029/receipt.json) |
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
| Two bounded Azure diagnostics and cleanup | `azure-sequence-20261027/` |
| Latest coverage ledger and completed batches | `point3-coverage-queue-20261026/` |
| Coverage failure classification | `coverage-failure-ledger-20261030/` |
| Publication, retry and fresh-yield safeguards | `client-review-20261029-safeguards/` |
| Package-size behavior | `package-size-checks-20261030.json` |
| Oxylabs residential test | `oxylabs-bounded-20261030/` |
| Oxylabs Web Unblocker test | `web-unblocker-bounded-20261030/` |
| Scrape.do Store 100 test | `scrapedo-bounded-20261030/` |
| Bright Data Store 100 test | `brightdata-bounded-20261030/` |

Evidence folders contain review-safe exports and their own hashes where applicable.

## Historical annex

Older 500-product demonstrations, 33-product samples, failed runs, transport experiments, screenshots and previous frozen packages remain in this folder for audit history. They must not be combined with current result counts.

## Private evidence

Full HTML responses, browser profiles, cookies, session state and unredacted captures remain outside Git under ignored local `data/` storage. Public evidence contains reviewed fields, hashes and redacted copies only.

## Open limits

- Full category and pagination coverage remains incomplete.
- No qualifying genuine volume or digital discount offer was found in bounded live review.
- Corrected re-fetch evidence does not prove one retry prevents future store drift.
- Two bounded Azure diagnostics completed. The Store 100/PICKUP control passed in two regions, but the following Art Sets listing was blocked in both.
- No tested transport has yet proved Store 100, ZIP 72712, PICKUP, product identity and local price together reliably enough for the final uncapped run.

No client message or contest submission is performed by repository tooling.
