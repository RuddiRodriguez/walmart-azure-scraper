# Current review status

## Fresh controlled sample

Authoritative live source:e90c5f0. Entry point:controlled_collection.py, reject-and-continue mode.
Plan/instructions:docs/CONTROLLED_COLLECTION.md. This mode writes review evidence only, not a
production latest pointer. Original full-crawl entrypoint scrape.py remains separate.

| Measure | Observed result |
|---|---:|
|Accepted distinct products|506|
|Required parent categories represented|11|
|Rejected product responses|11|
|No local pickup|4|
|Listing price missing for comparison|7|
|Wrong-store/identity responses in this run|0|
|Page/product processing errors|0|
|Local unavailable products retained|35|
|Runtime seconds|2063.272|
|Product/control Fetch requests|519|
|Listing Fetch requests/native pages|18 each|
|Original Fetch-body hashes verified|537|
|Native serialized-DOM hashes verified|18|
|Independent accepted-record source replays|506|

Both initial/final store controls passed100/72712/PICKUP. No duplicates or schema validation errors.
Every accepted row was matched to a rendered visible card, separately captured primary-listing
item, product identity/store/local pickup evidence and price. Bad responses were not inserted or
re-fetched. Offline tests verify wrong-store/identity continuation and access-block stopping.
This run did not encounter a wrong-store response, so it does not prove the transport issue fixed.

Actual JSON:evidence/controlled-skip-invalid-20261025/products.json.
Audit:evidence/controlled-skip-invalid-20261025/summary.json.
Safe source fields, request metadata, page decisions and checksums are in the same folder.
Complete original bodies/native DOM/private session evidence/unreviewed redaction drafts stay local.
Fetch originals are complete decoded body bytes, not compressed/TLS wire captures. Browser-generated
request headers/cookie values are not logged; request settings and allowlisted response headers are.

## Missing fields and unavailable products

Missing source values remain empty strings as the brief requires. UPC observed488/506, package
weight 331/506, PPM 386/506. GUPC and normalized unit_price remain blank at scraper stage. No missing
weight/UPC/PPM or deal amount invented. All35 local unavailable records retain blank regular/sale
prices rather than copying shipping prices. Source availability and missing-field counts are in
the audit. The dataset contains genuine distinct products, including these unavailable products.

## Bounds and costs

One run only: target 506,minimum 5each category,max750 product Fetch requests,80 captured listing Fetch
responses,3600 seconds,25-second per request/oneattempt. Native lazy settling capped20 scrolls/page;
10 ordinary exception ceiling also bounds failed page attempts. Browser setup/UI/assets generate
additional requests not individually counted.1024 MiBmaximum original bodies,10 MiB/body,8 GiBfree
reserve. Local Python/Chrome; no paid scraping API/proxy. Observed values stayed within these bounds.

## Separate prior evidence

Historical500, fresh33samples,67-product diagnostic and failed79/68controlled attempts are separate.
Do not combine their overlapping counts with this fresh506dataset. The failed79/68attempts captured
two actual complete private wrong-store/corrected same-session Fetch pairs, for14898365and51237368.
Safe hashes/settings/context/price metadata are in evidence/controlled-500-20261025/ and
evidence/controlled-500-continuation-20261025/. Privacy-reviewed sharing bodies/access remain pending.
One or two corrected re-fetches are not a demonstrated remedy.

## Open requirements

- Full uncapped category scope/queue exhaustion.69 prior associations and3 new independent landing
  URLs remain uncertain; ArtAprons empty HTTP200category route remains unresolved. ArtSets is valid
  but does not replace ArtAprons coverage. Pending queue counts remain in the fresh sample report.
- Genuine volume/digital deal examples:zero verified. New dataset has no deal examples.
- Repeated complete collection and sustained reliability.
- Final-version interruption/resume for this controlled wrapper. Existing production-core3-product
  SIGKILL/resume proof applies only to its recorded source/config/scope, not this new wrapper.
- Raw-pair reviewed sharing copies/access and refreshed full package/manifest/unsent client draft.
- Azure:no access granted, no deployment/test executed.

No production acceptance or full project completion claimed. Nothing sent/submitted to client.
