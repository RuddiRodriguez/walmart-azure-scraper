# Corrected step 3: evidence review and smallest proposed change

Status: proposal only. No collector change, live request, transport remedy or reliability claim.
Reviewed source: 859d3ef; diagnostic runner tested live at f7c535d.

## What the evidence supports

- Historical rejected item 857115210 reported store3081, ZIP95829, SHIPPING while the visible banner remained Bentonville100. The saved rejected product is parsed JSON, not a complete original HTTP body. The subsequent same-session fetch and navigation reported100/72712/PICKUP, but those saved HTML artifacts are serialized pages. They are not the requested complete raw pair.
- The earlier matched six-target comparison passed both the existing session and fresh small batches. It establishes no advantage for batching or session resets.
- Latest corrected step2 completed17 products and four first-page listings in120.933 seconds, with21 complete saved Fetch-decoded bodies verified offline. Every observed response matched100/PICKUP. It did not reproduce the longer failure, issue a re-fetch, or request historical failed item857115210.
- browser.py already uses browser-session Fetch with cache:no-store and default same-origin credentials. Latest valid responses include a cache-status:Hit listing and cache-status:Miss product. These successful responses and absent historical raw headers cannot establish a cache cause. Adding cache busting, explicit equivalent credentials, custom cookie copying, proxies or a new Python HTTP library has no demonstrated causal support.

## Smallest supported safety change to implement next

Strengthen scrape.verify_listing_store for listings whose candidates are about to be accepted: require explicit matching pageProperties.stores and the Pickup fulfillment facet. Reject missing or contradictory evidence before queueing their products. Existing product checks remain mandatory: identity, store, ZIP, intent, local pickup and listing/product price agreement.

Keep navigation-only category pages separate: they may lack product-store context. Such pages may supply discovery links but cannot establish local product prices. Do not blindly reject every navigation page or silently discard its children. Record why context is unavailable and leave full coverage incomplete where it cannot be established.

Offline review of the current function (listing-guard-review.json) shows: wrong store rejected; missing store, missing Pickup and Shipping accepted. This is a verified safety gap in the listing guard, not proof wrong prices reached published output: downstream product validation already provides another check. The bounded diagnostic runner already applies stricter listing validation; the proposal brings the production candidate gate into line with that evidence.

## Smallest transport/session hypothesis, still unproven

Do not alter transport merely because a short test passed. If genuine drift recurs, preserve the complete rejected body and attempt the already planned single identical same-session re-fetch for the required evidence pair. Both remain diagnostic; the failed collection stays invalid.

If that re-fetch remains wrong, a separately bounded candidate experiment is one fresh guest session, explicit normal store/Pickup selection, then re-discovery of the exact item on a verified current listing and a captured product fetch. Limit to one new session, one listing and one product response, five minutes; stop on access challenge. Do not merge the result into the failed run or call it a same-session correction. Extra browser/UI asset requests must be disclosed. No paid service or Azure. A fresh session is a hypothesis, not an established fix, and the previous successful small-batch comparison does not validate it.

## Detection and data preservation

Explicit drift: reject wrong store, ZIP, fulfillment intent or product identity in response fields.
Silent relative to the banner: inspect every product response and product-bearing listing rather than trusting banner/cookie names or unchanged prices. Reject missing/contradictory context. Responses with internally consistent but factually false store metadata cannot be conclusively detected by these checks; independent retailer confirmation would be needed. Do not promise universal silent-drift detection.

Do not equate unavailable with wrong-store: retain correctly identified local unavailable products under existing rules, with blank local prices where no local offer supports a price. Wrong/unverifiable context must not overwrite last good output. Existing bounded unavailable/recovery evidence keeps its limited scope; changing the production guard will require affected regression checks and source/config comparison before reusing recovery claims.

## Completion gates

1. Implement only the listing safety change, with checks for matching, wrong, missing and conflicting context plus navigation-only discovery. Existing10capture checks do not prove this new behavior.
2. Validate affected unavailable/last-good safeguards offline. Distinguish synthetic checks from live evidence.
3. Keep raw-pair requirement open until genuine complete wrong/correct bodies, safe request metadata, sequence, hashes and privacy-reviewed sharing copies exist.
4. No claim of a drift remedy until a controlled fault comparison and repeated meaningful live collection support it. A clean17-product attempt is insufficient.
5. Real offers, full uncapped coverage and repeated complete collection remain open. Existing bounded interruption/resume does not establish full/default/Azure recovery. Azure access remains ungranted.

Step3 review/proposal is complete. Implementation and transport validation are not complete. No client message sent.
