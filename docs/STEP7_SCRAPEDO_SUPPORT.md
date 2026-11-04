# Step 7 — Scrape.do support request

Sent 1 November 2026 at 10:24 Amsterdam time through the authenticated Scrape.do dashboard chat.

Support received the updated result:

- Store drift improved.
- Direct Store 100 targeting remains unsupported.
- Explicit PICKUP proof remains missing.

The message asks for the exact supported endpoint and parameters returning Store 100, ZIP 72712,
PICKUP, product ID and local price together. Nearby-store substitution is not acceptable.

Support replied on 2 November with the store-scoped endpoint and exact field paths. The bounded
test ran on 4 November:

- Three requests total, no retries, 45.233 seconds.
- All three responses proved product identity, Store 100, ZIP 72712, explicit PICKUP and local price.
- The pumpkin control returned PICKUP OUT_OF_STOCK at $2.97.
- The milk control returned PICKUP IN_STOCK at $2.88 twice.
- Scrape.do charged 10 existing credits per successful request, 30 credits total. No larger paid
  collection was started.

The planned 15-credit limit was exceeded because this endpoint charged 10 credits per request,
not the earlier observed 5. This deviation is recorded in the machine-readable result. No further
request was made. Future three-request limits must allow 30 credits.

Status: the product-page store-context gate passed. Category/listing coverage remains untested
through this endpoint, and no full paid collection is authorized.

Support request: `evidence/scrapedo-support-20261101/RESULT.json`.

Bounded result: `evidence/scrapedo-store-controls-20261104/RESULT.json`.
