# Client status — 5 November 2026, Amsterdam time

This checkpoint follows the client's review of the 4 November Scrape.do product controls. It
does not claim full coverage, listing-route proof, a clean fresh collection, recovery/repeat
completion, or Azure completion.

## Preserved evidence

- All three original Scrape.do responses remain in the private ignored evidence directory.
- Their SHA-256 hashes exactly match the hashes in
  `evidence/scrapedo-store-controls-20261104/RESULT.json`.
- Sanitized provider request IDs, per-request credit use, remaining-credit headers, runtime,
  requested product IDs, Store 100, ZIP 72712, PICKUP state and local prices remain in that
  result.
- No repeat or expanded Scrape.do test has run since the client requested the hold.

## Current open work

- 780 pending coverage pages.
- 216 retryable failures.
- 9 unresolved failed page types and 9 unresolved navigation pages: 18 total.
- Category/listing access through a verified Store 100, ZIP 72712 and PICKUP route remains
  unproven.
- Clean fresh collection, larger current-version recovery/resume, repeat collection and Azure
  completion remain separate and open.

The saved ledger still reports `full_coverage_complete: false` and
`publication_allowed: false`.

## Current execution state

- No Walmart or Scrape.do collector is running.
- No new provider credits have been used.
- No paid collection or Azure work has started.
- The repository evidence link is valid.
- Internal storage currently has about 515 GiB available, above the project guard. Storage is
  not approval to execute.

## Next proposed step

The separate bounded listing-route proposal is in
`docs/SCRAPEDO_LISTING_ROUTE_PROPOSAL_20261105.md`. It is a proposal only. No request may run
until the client explicitly approves it.
