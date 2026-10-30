# Bright Data bounded Store 100 test

Tested 30 October 2026 using one control-product input only.

## Result

Bright Data accepted the requested Walmart product URL, ZIP `72712`, and Store `100`. The job reached `Ready`, but produced zero successful records.

The downloaded result identified the exact cause: Walmart presented a CAPTCHA (`#px-captcha`) before Bright Data could collect the product record.

## Input

- Product ID: `47428850`
- ZIP: `72712`
- Store: `100`
- Snapshot: `sd_mvusfwz5q7zjwupad`
- Inputs: `1`
- Collection time: `1min10s`
- Success rate: `0.00%`
- Successful records: `0`

No price, availability, or PICKUP evidence was returned. Nothing from this test was accepted or published.

Sanitized machine-readable evidence: `evidence/brightdata-bounded-20261030/RESULT.json`.

The raw downloaded result remains private and is represented by its SHA-256 hash in the evidence file. Account credentials are not stored in Git.

## Status

Step 1 remains in progress. This single Bright Data test did not prove Store 100, ZIP 72712, PICKUP, product identity, and local price in the same collected response. It cannot be used to resume the full collection.
