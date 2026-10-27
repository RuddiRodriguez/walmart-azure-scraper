# Final client review status — 27 October 2026

Authoritative package version: `review-20261027-final-client`.
Exact package commit is recorded in `evidence/final-review-20261027/receipt.json` after the tag is frozen.

## What works

- Bentonville Store 100, 406 S Walton Blvd, ZIP 72712, PICKUP is verified from listing and product data. A correct banner alone is never accepted as proof.
- Wrong-store, wrong-product and unsupported local-price responses stay outside accepted output.
- Two privacy-reviewed wrong-store/corrected-response pairs preserve product, store, fulfillment, price, request sequence and retry information without cookies or session secrets.
- Eligible unavailable products remain in the catalog indefinitely. Unsupported current values stay blank. Earlier supported observations retain their original dates.
- Two separate 506-product live samples cover all 11 required parent categories. Both passed source, schema, duplicate, store, pickup and price checks.
- One 506-product run was killed after 100 saved products and resumed to 506 without losing or duplicating committed records. A separate 506-product repeat also passed.
- Current production collector passed a fresh smaller SIGKILL/resume test and an identical-settings repeat. Both returned the same three products and prices.
- PPM is copied directly from Walmart source text. Missing values are not invented.

## Evidence

- Wrong/correct response pairs: `evidence/response-pairs-reviewed-20261026/`
- Rejection and retention trace: `evidence/retention-step2-20261026/`
- 506-product recovery run: `evidence/point3-20261026/recovery-506/`
- Separate 506-product repeat: `evidence/point3-20261026/repeat-506/`
- Larger recovery checks: `evidence/point3-20261026/recovery-reevaluation.json`
- Current collector recovery: `evidence/phase-e-recovery-20261027/`
- Current collector repeat comparison: `evidence/phase-e-repeat-20261027/`
- Category review: `evidence/phase-c-bounded-200-20261027/`
- Offer review: `evidence/phase-d-offers-20261027/`

Every evidence folder contains review-safe files and hashes. Full HTML, browser profiles, cookies and session data remain private.

## Honest remaining limits

Full category and pagination coverage is not complete. Current cleaned review state contains 1,701 reviewed pages, 89 failed pages, 9 unresolved navigation-scope pages and 2,079 pending pages. The bounded 200-page continuation reduced the queue and did not recreate the earlier runaway growth.

No qualifying genuine volume or digital discount offer was found. The focused live review checked four searches and 13 distinct products at Store 100. Financing, cashback, Walmart Cash, ordinary Rollback and Clearance were not mislabeled as requested offers. No example was fabricated.

The two response pairs prove detection, rejection and a corrected re-fetch. They do not prove that one retry prevents future store drift.

Azure planning and execution are separate from this local package. No Azure execution is claimed.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scrape.py --store 100 --sample 2
```

Resume matching code and configuration:

```bash
.venv/bin/python scrape.py --store 100 --sample 2 --resume
```

See `docs/OPERATIONS.md` for full operation and `docs/VERIFY_PACKAGE.md` for package checks.
