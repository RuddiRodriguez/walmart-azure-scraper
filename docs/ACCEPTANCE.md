# Acceptance record

Latest results are in `docs/REVIEW_STATUS.md`. The earlier counts below are historical.
October 23 work added a 259-record broader partial attempt, a 57-record current-core live run,
three genuine unavailable records, 11 passing visible-price spot checks, and page/product-stage
SIGKILL recovery. A repeat failed on location context; resource guards stopped long testing.
Full catalog coverage, stable full repeats, genuine deal cases and Azure remain outstanding.

## Proven in earlier local feasibility run

- 500 unique records across all 11 configured parent categories.
- Store 100 pickup and Walmart seller checked for each accepted product.
- Current listing/product prices matched.
- 468 UPCs preserved; 381 displayed PPM values; zero duplicate IDs/URLs.
- Two earlier fresh sessions retained store/pickup across two Fresh Fruits pages.
- Earlier detail collection resumed from saved results after deliberate interruptions.

These results are in `evidence/`. They do not prove this new runner's full traversal.

## Required before production acceptance

- Fresh observed full run on the client-assigned store, confirming every category/subcategory.
- Product-page comparisons for random items, price types, UPC, PPM and package weight.
- Genuine live volume and digital deals, including all conditions. Do not invent examples.
- Complete repeated runs and measured duration/yield comparison.
- Page/product hard-kill recovery has passed locally; repeat it on the final client environment.
- Challenge/zero-yield/location-mismatch cases must leave the latest good output intact.
- Azure VM installation, outbound access, scheduling, logs, operational alerts and resource usage.
- Recorded walkthrough on the agreed environment, defect-support period and final transfer terms.

The package is a working implementation under validation, not a claim that these checks already passed.

## Packaged runner checks completed locally

- Live sample: 22 new records, exactly two per each required category; sample validation passed.
- Full publication stayed disabled; no latest.json was created for the deliberately partial sample.
- Saved-page resume: the three completed checkpoint pages were each recorded once, without repeat
  processing after interruption.
- Same-store overlap: a simultaneous second process exited with the file-lock error.
- Offline parser replay: all 500 historical records matched source fields checked by replay_evidence.py.
- Seven synthetic promotion examples from the specification were classified without inventing prices.
  These are clearly labeled synthetic, not live retailer offers.
- Python compilation and Ubuntu installer shell syntax passed.

Evidence: evidence/live-smoke/, evidence/recovery-check.json, evidence/overlap-check.txt,
evidence/replay-report.json and evidence/promotion-spec-examples.json.
