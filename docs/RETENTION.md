# Retention after client feedback — step2

Both current entrypoints, controlled_collection.py and scrape.py, enable retention explicitly.
Legacy product_record default remains available only for replaying earlier evidence; new callers
pass retain_missing=True. No old506dataset or frozen version has been changed.

## Rules

- Identity,store100,ZIP72712,PICKUP and primary-listing context still required. Bad context never
  supplies local prices or overwrites a last good product. Failed observation remains in history.
- A verified local offer, verified listing pickup, explicit local out-of-stock or prior proven
  store-assortment observation establishes eligibility. Matching generic store location alone does
  not establish that an online-only product belongs to this store's assortment.
- Correctly identified eligible unavailable products stay indefinitely, with unavailable current
  prices/deals/PPM blank. No shipping price is copied. Missing seller on unavailable PDP can use
  the directly observed retailer seller on its verified listing; explicit third-party seller conflicts
  remain exclusions. Price disagreement or missing listing price retains eligible identity with
  blank unsupported prices. It does not mean out-of-stock.
- Unproven store-assortment cases stay in assortment-review.json with blank local values, separate
  from confirmed eligible products. They are never silently dropped or labelled unavailable.
- Local explicit OUT_OF_STOCK/UNAVAILABLE is distinguished from no pickup offer, missing pickup
  evidence, missing availability evidence and missing price comparison. State lives in a separate
  status/history file; required product schema remains unchanged and values remain strings.
- Directly scraped PPM is never calculated. Unsupported/local-unavailable PPM is blank. Volume and
  digital offer fields remain separate. No new genuine-offer proof is claimed.

## Persistent history

Store-scoped SQLite catalog stores current retained products plus append-only, dated observations.
No expiry, deletion, “not seen” removal or fresh date assigned to carried data. Transactions update
history/current together; duplicate resumed observations are idempotent. Older replay cannot replace
newer observation. Store signature rejects cross-store reuse. Keep catalog files and their backups;
intentional filesystem deletion would remove local history. No software can retain deleted storage.

Review collector default: data/catalog/store-100.sqlite (plan may set catalog_path). Its products.json
remains fresh-run-only so sample counts never incorporate carried records. Separate retained-products,
assortment-review,retention-status,observation-history exports show accumulated history.

Full collector: <output>/100/catalog.sqlite. Existing latest published rows are imported with their
original crawl_date. Full products.json includes prior eligible products even when absent from a new
run. carried_observations and dated sidecar explain what is carried. Sample mode remains fresh-only.
Last-good publication gates remain in force; history/checkpoint export does not imply publication.

A correctly observed new unavailable item replaces its current values with blanks; its earlier
priced observation stays in history with original date. An invalid response does not overwrite the
last good row, whose old date remains visible. No claim that this old price is newly observed.

## Evidence and scope

See evidence/retention-step2-20261026/: all15requested rejected responses covering12products traced
against saved complete product responses and native/captured listing evidence. Two original506JSONs
remain byte-identical. Repaired catalog/history is explicitly offline historical replay, not a fresh
collection or a merged500claim. Exact capture versions and hashes accompany the trace; new replay
version/hashes appear in summary.json.

Run offline checks:

```sh
python -m tools.check_retention
python -m tools.check_controlled_collection
python -m tools.check_runner_flow
python -m tools.check_review_changes
```

Retention tests cover missing price/conflict, unavailable/missing pickup, seller evidence,
wrong context, old/unseen carry-over, original dates, indefinite/no-expiry retention, reopen,
deduplication and store isolation. Collector/full-mode tests verify actual caller wiring.
No new live/full/recovery/repeat/Azure proof is inferred from these offline checks. Changed source
requires separately scoped live tests under client's step3. Nothing sent to client.
