# Scrape.do listing-route proposal — 5 November 2026

Status: proposed only. Executable safeguards revised and tested offline on 8 November 2026.
No provider request has run and no client authorization has been given.

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

Scrape.do support confirmed on 7 November 2026 that the store endpoint supports category URLs
and supplied this request format:

```text
GET https://api.scrape.do/plugin/walmart/store
    ?token=<KEYCHAIN_TOKEN>
    &url=<URL_ENCODED_WALMART_LISTING_URL>
    &zipcode=72712
    &storeid=100
```

Proposed Walmart listing control:

```text
https://www.walmart.com/browse/food/milk/976759_9176907_4405816
```

The token stays in macOS Keychain. It must not appear in Git, logs, reports or commands saved as
evidence.

## Hard cumulative limits

- Maximum requests, including retries: 3.
- Intended sequence: one listing request, one exact repeat only if the first response passes,
  and one retry only for HTTP 502.
- Maximum retries: 1.
- Maximum provider usage: 60 existing credits total.
- Reserve 20 credits before every request, based on the client's observed 20-credit case.
- Maximum accepted reported usage per request: 20 credits.
- Persisted request deadline: 5 minutes after the process lock is acquired and state starts.
- Deadline cancellation may use up to 4 additional seconds for two termination joins.
- Process-lock waiting, post-response parsing, validation, evidence writes and report writes are
  outside the 5-minute request deadline.
- Maximum monetary spend: $0. Existing provider credits still have usage value.
- Maximum raw evidence: 20 MiB.
- Maximum response body: 8 MiB.
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
7. That product's explicit currently available PICKUP state.
8. The price and PICKUP evidence are linked inside that same product object.

Missing fields, a nearby store, SHIPPING-only context, challenge page, wrong category, inferred
values or mixed responses fail the control.

## Stop rules

Stop immediately when any condition occurs:

- First response shows the endpoint does not support a listing URL.
- Wrong or missing store, ZIP or PICKUP context.
- Provider reports more than the reserved 20 credits for one request.
- Cumulative use reaches 60 credits.
- A usage header is missing, invalid or cannot be reconciled.
- One HTTP 502 retry fails.
- Persisted 5-minute request deadline is reached.
- Token acquisition exceeds 10 seconds.
- Request or body-read child process reaches the persisted absolute deadline.
- A returned response completes at or after the absolute deadline.
- The remaining absolute deadline cannot safely contain the next request.
- One response exceeds 8 MiB or cumulative bodies reach 20 MiB.
- Response cannot prove listing identity and at least one product/local-price/PICKUP record
  together.
- Any unexpected charge, unsafe response or credential exposure.

No alternate endpoint, extra product request or easier substitute may be used without a new
proposal and approval.

## Implemented safeguards

The proposed runner is `tools/run_scrapedo_listing_controls.py`. It is separate from the old
product-only runner and refuses execution unless the explicit `--approved` flag is present.

Before each request it saves the attempt and reserves its request and credit allowance. The
same saved state holds the absolute deadline, request count, retry count, body bytes and
accounted credits across restarts. An uncertain in-flight attempt blocks restart until it is
manually reconciled. One exclusive process lock covers state loading, admission, reservation,
request and result update. Saved state is validated before resume, and every atomic write uses
a unique temporary file. Redirects and alternate fallbacks are disabled.

Token lookup has a bounded subprocess timeout. The complete request and response-body read run
in a separate process under the persisted absolute deadline. At the deadline the child is
terminated, killed if needed, joined and checked as stopped. The two cleanup joins may add up
to four seconds after the deadline. Waiting for the exclusive lock, post-response parsing,
validation, evidence writes and report writes are outside that request deadline. A response
returned after the deadline is rejected after any reported usage is accounted. A wrong store, missing PICKUP
state, unlinked price, unexpected provider usage or incomplete two-control sequence cannot
pass.

Offline safeguard result: `evidence/scrapedo-listing-runner-20261106/OFFLINE_TESTS.json`.
Twenty focused checks passed. They include a real token-style subprocess timeout, a real
localhost trickle-body cancellation and two simultaneous processes sharing one allowance.
They made zero provider or retailer
requests and do not prove live listing support.

Provider charging remains uncertain: reserving 20 credits cannot prevent a provider from
reporting or charging more after a request. Such a result is preserved as unsafe and stops the
run; it is never converted to zero usage.

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
