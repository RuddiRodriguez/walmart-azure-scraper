# Current review status

## Latest client feedback: step2 retention addressed locally

Implementation4a68607 and offline trace: evidence/retention-step2-20261026/README.md.
All15rejected responses/12products accounted for:7missing-price,2confirmed-unavailable,
4unproven-assortment,2explicitmarketplace events. Eligible rows retained with blank unsupported
values; dates/history preserved indefinitely. Unknown assortment kept separately. Full output
carries prior eligible products; fresh review samples remain separate. 29retention/13collector/
16production-flow checks plus existing safeguard checks passed; no new live/full/recovery proof.
Historical accumulated catalog545eligible+2unverified/1027observations is not a new fresh collection.
Original506files unchanged. Other feedback steps and independent client acceptance remain open.


## Latest client feedback: step1 response-pair sharing preparation

Four source-verified redacted response copies and exact capture commits/module hashes are ready in
evidence/response-pairs-reviewed-20261026/. See its README for request sequence, unchanged preserved
fields, privacy review and limitations. Full originals remain private. This supersedes historical
“privacy review pending” notes for these copies only; no client delivery/acceptance or drift cure
is claimed. Other new-feedback requirements, especially rejection/retention, remain unaddressed
by this focused task. Existing review-20261026-step9 archive remains unchanged.

## Step 7 bounded repeat — completed

Same producer hashes, plan bytes, store/category/dependency settings and observed versions as first
run. Repeat source commit2ff5e20; first source e90c5f0. No collection code changed during either run.

|Measure|First run|Repeat|
|---|---:|---:|
|Accepted distinct records|506|506|
|Required categories represented|11|11|
|Rejected responses|11|6|
|Wrong-store responses excluded|0|2|
|Processing errors / duplicate IDs|0 / 0|0 / 0|
|Unavailable retained|35|35|
|Runtime seconds|2063.272|2048.379|
|Original body hashes verified|537|533|
|Native snapshot hashes verified|18|19|
|Accepted-record source replays|506|506|

Repeat rejections:2 wrong store,4 no local pickup. It continued without re-fetching; rejected values
never entered accepted JSON. Both initial/final controls passed. All accepted source replays and
schema/category/price/store checks passed. Effective runtime 0.72% shorter; this is an observation,
not a performance-improvement claim from unchanged code.

468 common IDs;433 comparable nonblank effective-price pairs unchanged. One common SKU 14898365
changed from available with local price 12.78 to locally unavailable with blank current local price.
38 IDs appear only in each sample; bounded sample membership is not product additions/deletions.
Field availability/count differences and item-level changes are in comparison.json.

Current repeat JSON/audit/comparison: evidence/controlled-skip-invalid-repeat-20261025/.
Previous baseline remains byte-identical to its frozen SHA. Native bodies/private session details
remain unshared. This satisfies the requested bounded repeat, not repeated uncapped full-category
collection. Current-wrapper recovery subsequently passed one three-product live SIGKILL/resume
test at45ba7c4 (evidence/step8-controlled-recovery-20261026/RESULTS.md). Full-catalog recovery
remains unproven. Full scope, offers, Azure and private-pair sharing remain open.

## First controlled sample (baseline)

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
- Repeated full uncapped collection and sustained reliability beyond the two bounded samples.
- Full-catalog recovery/every interruption point remains unproven. Current collector passed the
  separately scoped three-product live SIGKILL/resume at45ba7c4; no large run after recovery change.
- Raw-pair reviewed sharing copies/access remain pending. Updated public package and unsent draft
  frozen as review-20261026-step9; verification instructions in docs/VERIFY_PACKAGE.md.
- Azure:no access granted, no deployment/test executed.

No production acceptance or full project completion claimed. Nothing sent/submitted to client.

## Step9 review package

Frozen source/evidence version:review-20261026-step9. Includes separate two506datasets, current-source
recovery3, historical samples, source checks, safe logs/metadata, manifest and unsent client draft.
No new collection or Azure test during packaging. Exact tagged commit/local ZIP receipt recorded
after freeze in evidence/review-package-20261026/receipt.json on main. Raw originals remain private.
