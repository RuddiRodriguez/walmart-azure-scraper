# Step 5 — full offline regression

Result: passed.

All checks ran without browser, network, Azure, proxy or live retailer access.

| Check | Result |
|---|---|
| Safeguards | Passed |
| Unverified assortment gate | Passed |
| Package-size extraction | Passed |
| Two historical 132-product package replays | Passed |
| Historical retention behavior | Passed |
| Runner flow | Passed |
| Saved 500-source replay | Passed: 500 records, 0 errors |
| Taxonomy and coverage queue | Passed |
| Saved coverage ledger | Passed |

The current package parser changes the weight field for 43 records in each historical 132-product
dataset. No other fields changed. Original files were not rewritten.

Both 132-product datasets remain historical bounded runs. Both 506-product datasets remain
historical controlled demonstrations. Their product files passed hash checks and remain unchanged.
None is labeled as a clean current-version run.

Coverage remains incomplete: 780 pending pages, 216 retryable failures, 9 unresolved failed pages
and 9 unresolved navigation pages.

Full machine-readable result:
`evidence/full-offline-regression-20261031/RESULT.json`.
