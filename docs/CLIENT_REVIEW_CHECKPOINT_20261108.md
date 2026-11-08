# Client review checkpoint — 8 November 2026

Focused offline correction only. No Scrape.do, Walmart, Azure or other external request ran.
No provider credit was used. Proposed listing test remains on hold.

## Latest review requirements

| Requirement | Status | Evidence |
|---|---|---|
| Bound Keychain token acquisition | Complete offline | 10-second subprocess timeout and focused test |
| Hard deadline for request and body read | Complete offline | Cancellable child-process transport |
| Cancel and confirm cleanup at deadline | Complete offline | Terminate, kill if needed, join and verify stopped |
| Reject a response returned after deadline | Complete offline | Late result is rejected after reported usage is accounted |
| Real trickle-body regression | Complete offline | Localhost server cancelled at absolute deadline |
| Exclusive process ownership | Complete offline | File lock covers state load through final update |
| Race-free atomic state writes | Complete offline | Unique temporary file plus `fsync` and atomic replace |
| Validate resumed state | Complete offline | Version, counters, deadline, in-flight and completion checks |
| Two simultaneous-process regression | Complete offline | Two processes used one shared allowance and only two controls ran |
| Provider/retailer execution | Not started | Client hold remains |

## Focused results

Twenty focused checks passed:

- zero provider or retailer requests;
- one localhost-only trickle request;
- zero provider credits;
- real token-style subprocess timeout enforced;
- late response rejected;
- trickling body cancelled with child cleanup confirmed;
- two simultaneous runners serialized under one allowance;
- invalid resumed state blocked before token acquisition or dispatch.

Result: `evidence/scrapedo-listing-runner-20261106/OFFLINE_TESTS.json`.

## Provider configuration update

Scrape.do support confirmed on 7 November that its Walmart store endpoint supports category
URLs. The runner and proposal now use the exact Milk category example supplied by support:

```text
https://api.scrape.do/plugin/walmart/store
url=https://www.walmart.com/browse/food/milk/976759_9176907_4405816
zipcode=72712
storeid=100
```

This confirms supported configuration only. It does not prove live Store 100, ZIP 72712,
PICKUP availability, product identity and linked local price. Evidence:
`evidence/scrapedo-support-20261107/RESULT.json`.

## Still open

- Proposed maximum three-attempt/60-credit listing test: on hold.
- 780 pending pages.
- 216 retryable failures.
- 18 unresolved paths.
- Fresh collection, larger recovery/repeat and Azure work remain separate.

No live completion claim is made.
