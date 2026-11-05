# Scrape.do listing-route proposal — 5 November 2026

Status: proposed only. Not executed. No client authorization yet.

## Goal

Test whether one Walmart category/listing response can tie together:

- the requested category and page;
- Store 100;
- ZIP 72712;
- explicit PICKUP;
- product identity; and
- local product price.

The product-page controls do not prove this listing requirement.

## Candidate configuration

Scrape.do support recommended the store endpoint for product pages. Support has not confirmed
that it supports category/listing URLs. The proposed candidate request is:

```text
GET https://api.scrape.do/plugin/walmart/store
    ?token=<KEYCHAIN_TOKEN>
    &url=<URL_ENCODED_WALMART_LISTING_URL>
    &zipcode=72712
    &storeid=100
```

Proposed Walmart listing control:

```text
https://www.walmart.com/browse/personal-care/toothpaste/1005862_1007221_1023020?page=1
```

The token stays in macOS Keychain. It must not appear in Git, logs, reports or commands saved as
evidence.

## Hard cumulative limits

- Maximum requests, including retries: 3.
- Intended sequence: one listing request, one exact repeat only if the first response passes,
  and one retry only for HTTP 502.
- Maximum retries: 1.
- Maximum provider usage: 30 existing credits total.
- Maximum accepted per-request usage: 10 credits.
- Maximum runtime: 5 minutes total.
- Maximum monetary spend: $0.
- Maximum raw evidence: 20 MiB.
- No queue changes, publication, full collection, product-page expansion or Azure work.

Existing credits still carry usage cost. These limits are not authorization.

## Acceptance rules

An accepted response must independently prove all of the following from the same source:

1. Requested listing/category identity and page.
2. Store ID `100` and pickup store `100`.
3. Postal code `72712`.
4. Explicit `PICKUP` intent or fulfillment.
5. At least one product ID.
6. That product's local price.
7. That product's explicit PICKUP availability state.

Missing fields, a nearby store, SHIPPING-only context, challenge page, wrong category, inferred
values or mixed responses fail the control.

## Stop rules

Stop immediately when any condition occurs:

- First response shows the endpoint does not support a listing URL.
- Wrong or missing store, ZIP or PICKUP context.
- Provider reports more than 10 credits for one request.
- Cumulative use reaches 30 credits.
- One HTTP 502 retry fails.
- Runtime reaches 5 minutes.
- Response cannot prove listing identity and at least one product/local-price/PICKUP record
  together.
- Any unexpected charge, unsafe response or credential exposure.

No alternate endpoint, extra product request or easier substitute may be used without a new
proposal and approval.

## Evidence to preserve

- Original response stored privately.
- SHA-256 hash and byte size.
- Sanitized requested URL and parameters.
- HTTP status and runtime.
- Provider request ID and credit headers.
- Exact source paths used for category, store, ZIP, PICKUP, product ID and local price.
- Sanitized accepted or rejected result.

Passing this control would prove only the bounded listing route. It would not authorize or
complete the 780 pending pages, 216 retryable failures, 18 unresolved paths, fresh collection,
recovery/repeat or Azure work.
