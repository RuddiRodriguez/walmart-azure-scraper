# Client status — 4 November 2026, Amsterdam time

This checkpoint updates revision `8b7e03a`. It does not claim full coverage or a clean fresh
current-version collection.

## Completed since the previous checkpoint

1. Scrape.do support provided the store-scoped endpoint and exact field paths.
2. Three bounded product controls ran with no retries in 45.233 seconds.
3. Every response proved product identity, Store 100, ZIP 72712, explicit PICKUP and local price.
4. The pumpkin control returned OUT_OF_STOCK at $2.97. The milk control returned IN_STOCK at
   $2.88 twice.
5. The requests used 30 existing Scrape.do credits. No paid collection, Azure work or larger
   collection was started.
6. The four Walmart volume/digital fields are now always empty. Rollback is kept only in the
   applicable regular/sale price fields.
7. All ten offline regression modules pass on source commit `58851a9`.

## Limit deviation

The test planned for 15 credits based on the previous endpoint rate. The store endpoint reported
10 credits per successful request, so three successful controls used 30 credits. No further
request was made. Future three-request controls must use a 30-credit limit.

## Still open

- 780 pending coverage pages.
- 216 retryable failures.
- 9 unresolved failed page types and 9 unresolved navigation pages, 18 total.
- Category/listing access through the store-scoped endpoint is not proven.
- A clean fresh current-version collection, larger interruption/resume and repeat remain open.

Full collection has not resumed. It requires client approval for paid work and sufficient local
free space. The Mac currently remains below the project's 60 GiB stop threshold.

## Evidence

- Store controls: `evidence/scrapedo-store-controls-20261104/RESULT.json`
- Updated offline regression: `evidence/full-offline-regression-20261104/RESULT.json`
- Support history: `docs/STEP7_SCRAPEDO_SUPPORT.md`

Nothing was sent to the client by repository tooling.
