# Smallest paid transport proposal — 30 October 2026

Status: executed on 30 October 2026. See `docs/OXYLABS_BOUNDED_RESULT.md`.

## Recommendation

Use one Oxylabs residential proxy session with US ZIP `72712`. Keep the current Chrome browser,
store-selection flow, request order, parser, checkpoint and publication checks unchanged.

This is smaller than moving to Web Scraper API. A residential proxy changes only Chrome's network
route. Web Scraper API needs a new request adapter and separate proof that its returned pages keep
the same product, Store 100, ZIP, PICKUP, price, cookie and sequence evidence required by this
collector.

## Code change

Set `WALMART_PROXY_URL` before starting the existing command. The value is read only when Chrome
starts and is never written to repository evidence or application logs.

Example shape, with placeholders only:

```text
export WALMART_PROXY_URL='<username-with-US-ZIP-and-session>:<password>@<proxy-host>:<port>'
```

Oxylabs documents residential location routing down to country, state, city and five-digit US ZIP,
and sticky sessions through a session identifier in the authentication username.

## First bounded check

1. Start a clean output folder. Do not resume an earlier run.
2. Use one sticky US residential session targeted to ZIP 72712.
3. Select Bentonville Store 100 and PICKUP through the normal browser flow.
4. Load two known control products.
5. Load the Art Sets listing that Azure blocked.
6. Review no more than five candidate products.
7. Accept a response only when it independently proves product ID, Store 100, ZIP 72712, PICKUP
   and supported local price or unavailability.
8. Preserve a privacy-reviewed rejected/corrected pair if drift occurs. The run remains blocked from
   publication even if a retry is correct.

## Limits

- One session
- Maximum 15 minutes
- Maximum 2 control products, 1 listing and 5 candidate products
- Maximum 20 retailer requests, including retries
- Maximum 100 MiB proxy traffic
- One retry per failed target
- No full crawl and no production publication

Oxylabs published entry residential pricing was `$6/GB` when checked on 30 October 2026. At the
100 MiB traffic cap, usage is about `$0.59`. Set a hard test budget of `$1`, excluding any provider
minimum purchase or subscription. Confirm checkout price before purchase because pricing can change.

## Stop immediately when

- store, ZIP, fulfillment or product identity is wrong or missing
- a challenge or access-denied page appears
- two consecutive transport failures occur
- request, time, traffic or cost limit is reached
- evidence capture fails
- proxy credentials appear in output or logs

## Evidence to export

- source commit and configuration hashes
- redacted proxy mode and session sequence, never username or password
- request counts and runtime
- product/store/ZIP/PICKUP/price checks for every accepted response
- rejected response reason and corrected response context if drift occurs
- final publication decision

## Decision after test

- Continue to a larger bounded run only if all checks pass without silent drift or challenge pages.
- Stop and report failure if store proof is missing, drift repeats, or the listing remains blocked.
- Do not move to Web Scraper API automatically. Assess that larger adapter only if the residential
  proxy check fails and the client still wants another paid method.

## Result

The proxy location check reached Bentonville/ZIP 72712, but Walmart's store banner did not load.
The initial sticky session and one fresh-session retry both stopped before collection. No listing or
product response was accepted, and no production output was published. The provider dashboard
reported 14.38 MB, 55 total proxy requests and $0.09 displayed spending. This paid transport did not
pass the gate for a full collection.

## Official sources checked

- https://developers.oxylabs.io/products/proxies/residential-proxies/location-settings
- https://developers.oxylabs.io/help-center/products-and-features/how-to-use-session-control
- https://developers.oxylabs.io/help-center/getting-started/start-using-residential-proxies
- https://oxylabs.io/pricing
- https://oxylabs.io/products/web-api/scrape/ecommerce
