# Evidence index

## Current client evidence

Live summary: [`docs/CURRENT_PROGRESS.md`](../docs/CURRENT_PROGRESS.md).

| Requirement | Evidence |
|---|---|
| Final status and package receipt | `docs/FINAL_CLIENT_REVIEW_20261027.md`, `client-ready-v2-20261027/receipt.json` |
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

Evidence folders contain review-safe exports and their own hashes where applicable.

## Historical annex

Older 500-product demonstrations, 33-product samples, failed runs, transport experiments, screenshots and previous frozen packages remain in this folder for audit history. They must not be combined with current result counts.

## Private evidence

Full HTML responses, browser profiles, cookies, session state and unredacted captures remain outside Git under ignored local `data/` storage. Public evidence contains reviewed fields, hashes and redacted copies only.

## Open limits

- Full category and pagination coverage remains incomplete.
- No qualifying genuine volume or digital discount offer was found in bounded live review.
- Corrected re-fetch evidence does not prove one retry prevents future store drift.
- Azure execution is not included.

No client message or contest submission is performed by repository tooling.
