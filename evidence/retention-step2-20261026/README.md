# Rejection trace and retention result — step2

Implementation/replay source:4a68607d1f7581740a3403e1ba9d8c852fa08214.
This is offline replay of genuine previously collected responses, not new live collection.
Original506datasets are unchanged. Capture source commits/body hashes and exact dates are in rejection-trace.json.

All15requested rejection events covering12products accounted for:

| Product | Events | At rejected observation | Latest retained status from these two historical runs |
|---|---:|---|---|
|10533021|1|price_evidence_missing|available at 2026-10-25T23:10:58.142773+00:00|
|17941208051|2|assortment_unverified|assortment_unverified at 2026-10-25T23:03:54.785001+00:00|
|20109864798|1|price_evidence_missing|available at 2026-10-25T23:11:07.799470+00:00|
|20736762290|1|confirmed_unavailable|available at 2026-10-25T22:56:13.178994+00:00|
|20803673411|2|assortment_unverified|assortment_unverified at 2026-10-25T23:03:51.776084+00:00|
|2537720607|1|confirmed_unavailable|confirmed_unavailable at 2026-10-25T22:45:24.505136+00:00|
|35511656|1|price_evidence_missing|available at 2026-10-25T23:10:51.293330+00:00|
|5113125462|1|price_evidence_missing|available at 2026-10-25T23:10:48.227864+00:00|
|5212491762|1|price_evidence_missing|price_evidence_missing at 2026-10-25T22:21:26.164835+00:00|
|598478108|1|price_evidence_missing|available at 2026-10-25T23:10:44.890689+00:00|
|606723351|1|price_evidence_missing|available at 2026-10-25T23:10:54.761977+00:00|
|733110876|2|excluded_marketplace|Explicit third-party seller; excluded, rejection archived|

Seven missing-price events retained with blank price/deal/PPM values; these do not mean unavailable.
Six later independent repeat observations recovered supported prices, while5212491762still lacks
listing-price evidence in these saved runs. No current-day availability assertion is made.

Two genuine unavailable events retained, including absent PDP seller backed by verified Walmart
listing seller.20736762290later had a valid available observation; both dates/states remain in history.
2537720607remains unavailable at its historical observation date.

Two products(20803673411,17941208051)have a local context but no proof of store assortment. Four
events retained in assortment-review.json with blank local prices, not called confirmed unavailable
or added to validated local sample counts. Matching store banner/location alone is insufficient.

733110876was explicitly sold by Staples on both PDPs despite Walmart listing seller. Two marketplace
exclusions are legitimate under retailer-only scope; both archived. It was not an eligible local
Walmart unavailable product. Nothing silently dropped from the trace.

## Persistent repaired historical catalog

545eligible records,2assortment-unverified records,1027dated observations from1012previously
accepted rows plus15rejected responses. This is an accumulated historical catalog, never a fresh545
product demonstration. Fields remain required strings, unsupported current values blank. Earlier
priced observations are preserved with their original dates. No expiry or not-seen removal.

Review collector persistent store catalog bootstrapped from audited history with original dates;
future fresh products.json counts remain separate. Full collector imports last published data and
carries unseen eligible records into full outputs. No last-good publication pointer changed by
this task. See catalog-bootstrap.json and docs/RETENTION.md.

## Verification

29synthetic retention checks,13collector orchestration checks,16production flow checks passed.
Existing requirement and unavailable/last-good regressions passed separately. These cover durable
history/reopen,unchanged original dates,wrong-store protection,missing prices,no pickup,retailer
seller evidence,unknown assortment,old replay,deduplication,store isolation and full-mode unseen carry.

No new live collection,larger restart/repeat,full coverage,offers or Azure test was performed.
Step2code/trace/retention requirements addressed locally; client independent verification remains
pending. Two assortment-unverified products remain honestly unresolved for eligibility, safely
retained for review instead of labelled unavailable. Other client steps remain separate. Nothing sent.
