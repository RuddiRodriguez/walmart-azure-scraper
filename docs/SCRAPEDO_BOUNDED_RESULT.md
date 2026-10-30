# Scrape.do bounded Store 100 test

Tested 30 October 2026 using three requests only.

## Result

Scrape.do's structured product endpoint returned the control product for Store 100 in ZIP 72712 with the expected $3.97 price. The response and provider header both identified Store 100.

The response did not contain an explicit PICKUP field. It therefore does not meet the full acceptance rule and was not approved for collection.

## Three requests

1. Store-scoped control page: provider plugin failure (`502`).
2. Product endpoint with Store 100: provider reported Store 100 is not directly supported (`400`).
3. Product endpoint with ZIP 72712: returned Store 100, ZIP 72712, item `47428850`, and price `$3.97` (`200`), but no explicit PICKUP proof.

Ten of 1,000 free credits were used. No full collection ran. No returned product was published.

## One-request Search follow-up

The Search endpoint returned explicit pickup fulfillment, but silently changed the location:

- Requested ZIP: `72712`
- Returned store: `3479`
- Returned ZIP: `72756`
- Returned city: Rogers, Arkansas
- Control item: `47428850`
- Returned price: `$3.95`

This response was rejected because it did not represent Store 100. This also proves that requesting ZIP 72712 alone does not reliably pin Scrape.do's Search endpoint to Store 100.

The follow-up used another 10 credits. Total usage is 20 credits, with 980 remaining.

Sanitized machine-readable evidence: `evidence/scrapedo-bounded-20261030/RESULT.json`.

Raw responses remain private and are represented by SHA-256 hashes in the evidence file. API token remains in macOS Keychain and is not stored in Git.

## Status

Step 1 remains in progress. Scrape.do cannot currently meet the acceptance rule: its Product endpoint identified Store 100 but omitted PICKUP, while its Search endpoint included PICKUP but returned Store 3479. Next supported route is provider support enabling direct Store 100 selection, or another transport that can prove Store 100 and PICKUP in the same response.
