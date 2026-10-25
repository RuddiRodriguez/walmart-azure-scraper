# Step 1 — baseline and evidence inventory, 25 October 2026

Scope: inventory and documentation only. No collector changes, live scraping, new acceptance
suite, Azure execution or client communication. No live collectors were found.

## Confirmed demonstration context

The client feedback supplied by the user accepts Bentonville #100, 406 S Walton Blvd,
AR 72712, PICKUP for the next bounded demonstration. This supersedes the earlier note that the
demonstration location was unconfirmed. It does not grant Azure access or establish a production
store assignment. The banner alone remains insufficient evidence.

## Authoritative baseline

- Frozen review tag: review-20261024-final.
- Package source commit: 415a7c23d09b2fce113f8550b0b4474bd0a6f4d0.
- Repository HEAD before this inventory: 04c157e2cae106ee4cb2ffbb32408d8bda8b693c.
- Frozen archive SHA256:79ec1bfa0d2424ce31b9ebe528216dfceea41d2e1dc99a8b7421277891cd1d3f.
- Local archive present; its bytes match the existing receipt hash.
- Anonymous HEAD requests returned HTTP200 for the frozen source page, historical JSON and
  source ZIP. No response bodies downloaded in these accessibility checks.
- This inventory is a subsequent documentation update; it does not move or replace the frozen tag.

[Source](https://github.com/RuddiRodriguez/walmart-azure-scraper/tree/review-20261024-final)
[JSON](https://raw.githubusercontent.com/RuddiRodriguez/walmart-azure-scraper/review-20261024-final/evidence/products-500.json)
[Source ZIP](https://github.com/RuddiRodriguez/walmart-azure-scraper/archive/refs/tags/review-20261024-final.zip)

## Separate datasets

| Evidence | Count | Meaning |
|---|---:|---|
| Earlier live demonstration |500 distinct products, 11 parents|Historical; unchanged SHA256; not a fresh final-runner result|
| diagnostic-c |33|Fresh sample; source audit passed; 613.89 seconds|
| repeat-d |33|Fresh sample; same 33 products/prices; 596.86 seconds|
| fresh-506-a |32|Failed on store banner; 301.91 seconds; no publication|
| fresh-506-c |64|Failed on product location; 631.46 seconds; no publication|

Do not combine overlapping records or label either failed partial run as a successful collection.
Existing validation/source-audit results are inventoried here, not rerun.

## Exact mismatch evidence

Product 857115210, Clorox: listing displayed $6.26. Saved rejected product data reports
Store 3081,ZIP 95829,SHIPPING. Subsequent same-page fetch and native navigation report
Store 100,ZIP 72712,PICKUP. All three product snapshots show $6.26 and Walmart.com seller.
Matching prices therefore do not prove the correct local store.

Available privately:

- Parsed rejected product/candidate JSON, including location and price context.
- Parsed/reserialized listing HTML associated with the candidate.
- Parsed/reserialized corrected HTML from same-page fetch and native navigation.

Available publicly:

- Sanitized rejected source projection, collection events, response status/cache/date metadata,
  probe sequence/context and hashes under evidence/final-session-20261024/fresh-506-c/.

Important capture gaps:

1. No complete original wrong-store HTTP response body retained.
2. Corrected HTML was written from BeautifulSoup objects. These are reserialized snapshots,
   not untouched response bodies or exact wire bytes.
3. Full redacted request settings were not captured at request time; code/configuration can
   describe intended settings but cannot retrospectively prove every actual request.
4. Probe ordering is known, but complete per-request timing/session evidence is missing.

Existing source data remains useful, but does not satisfy the requested paired complete raw
response evidence. Do not reconstruct or mislabel a missing original response. Step 2 must capture
bodies before parsing and preserve originals privately plus redacted sharing copies/hashes.

## Environment and dependencies

Local macOS 27.0.1, arm64; Python 3.14.5; Chrome 155.0.8059.85; SeleniumBase 4.56.3;
BeautifulSoup 4.15.0; psutil 7.2.2. Collector uses local Chrome and in-browser product fetch.
Exact core/configuration hashes, file hashes and byte counts are in
`evidence/diagnostic-20261025/baseline-inventory.json`.

Service dependency: Walmart must return sufficient consistent listing/product evidence for
Store 100/PICKUP/local prices. No paid proxy or API configured. No Azure access granted.

## Step 1 result and next gate

Baseline established; datasets separated; frozen package accessible; capture gaps documented;
demonstration store confirmation recorded. No store-consistency fix claimed.

Outstanding acceptance: paired raw responses, sustained store correctness, full uncapped
coverage, repeated complete collection, genuine live offers, final-version live interruption/
resume and Azure execution. Step 2 requires user instruction; no new run started.
