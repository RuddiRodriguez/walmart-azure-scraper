# Client review checkpoint — 6 November 2026

This checkpoint answers the latest review. It covers offline evidence and safety corrections
only. It does not claim provider listing support, full coverage, a fresh collection,
recovery/repeat completion or Azure completion.

## Requirement check

| Client request | Status | Evidence |
|---|---|---|
| Privacy-reviewed copies or bounded excerpts from all three product controls | Complete | `evidence/scrapedo-store-controls-20261104/source-excerpts/` |
| Original and excerpt hashes plus redaction description | Complete | `source-excerpts/MANIFEST.json` |
| Separate displayed pumpkin price from an available pickup offer | Complete | Request 01 is explicitly OUT_OF_STOCK and not claimed as an available offer |
| Preserve exact run producer or a verifiable current-version comparison | Complete | `run-producer.py` and `PRODUCER_PROVENANCE.json` |
| Listing-specific runner | Complete offline; not executed live | `tools/run_scrapedo_listing_controls.py` |
| Reserve request and credit limits before dispatch | Complete offline | Persistent state is saved before token retrieval and request dispatch |
| Stop after wrong context or unexpected usage | Complete offline | Focused safeguard checks |
| Persist counters and uncertain attempts across restart | Complete offline | Focused safeguard checks |
| Absolute deadline, response-byte limit and no redirects/fallbacks | Complete offline | Focused safeguard checks |
| Missing or invalid credit headers must not become zero | Complete offline | Focused safeguard checks |
| Require allowed PICKUP availability and linked product price | Complete offline | Focused safeguard checks |
| Intended control sequence must finish before passing | Complete offline | Focused safeguard checks |
| Full ten-module offline regression | Complete locally | Ten of ten modules passed; no network used |
| Regenerated final manifest | Complete | 1,752 listed files verified in `evidence/SHA256SUMS.json` |
| Provider listing-route proof | Not started; client hold remains | No provider request or credit used |
| 780 pending, 216 retryable and 18 unresolved | Open | Coverage ledger remains unchanged |

## Source-response clarification

The three private source files still match their original hashes. The public excerpts retain
only the exact location, product, displayed-price and PICKUP fields needed for review.

- Pumpkin `47428850`: Store 100, ZIP 72712 and PICKUP are present, but the PICKUP state is
  `OUT_OF_STOCK`. The displayed `$2.97` is not a currently available pickup offer.
- Milk `10450114`, repeated twice: Store 100, ZIP 72712, PICKUP and `IN_STOCK` are present.
  The displayed price is `$2.88`. The price and PICKUP option are under the same product
  object, but the PICKUP option contains no separate fulfillment-specific price.

## Listing proposal status

The new listing runner has not contacted Scrape.do or Walmart. Fourteen focused offline checks
passed with zero network requests and zero provider credits. The proposed cumulative limits are
three attempts including one HTTP 502 retry, 60 existing credits reserved at 20 per attempt,
five minutes, 8 MiB per response, 20 MiB total response data and $0 monetary spend.

These limits are a proposal, not authorization. Provider charging cannot be guaranteed before
a response arrives. Missing, invalid or excessive usage is preserved as unsafe and stops the
runner; it is never counted as zero.

## Package verification

The final manifest lists and verifies 1,752 files. It now includes the 5 November status and
listing proposal, the current client-message draft, the exact November 4 producer, the bounded
source excerpts and the new listing-runner checks. The frozen archive passed its file inventory,
SHA-256 and ZIP integrity checks. Private raw responses remain outside the public package.

## Remaining work

Full coverage remains incomplete. The open ledger is still 780 pending pages, 216 retryable
failures and 18 unresolved paths. The two Sun Care mappings do not prove complete child
coverage. Fresh collection, larger current-version recovery/repeat and Azure work remain
separate.
