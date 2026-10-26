# Bounded collection with invalid-response rejection

Use existing project setup, then run once:

```sh
python controlled_collection.py --plan evidence/controlled-skip-invalid-20261025/plan.json --output data/new-review-run
```

Target506distinct valid products, minimum5in each of11required categories. Maximum750product
requests,80listing pages,3600seconds. Requests have one attempt. No automatic restart.

Every accepted product must independently match configured store/ZIP/Pickup, identity, local offer,
seller and visible listing price. Wrong-store/identity responses are saved privately, logged and
skipped; they are never inserted or re-fetched. Other invalid products are excluded with reasons.
Listing context failures skip that page. Bad controls are recorded; they do not turn valid product
records into bad data. Access blocking, evidence/storage/budget failures and10ordinary exceptions
stop the run. Known unresolved category branches remain gaps.

Products/report checkpoint under data/. Original response bodies, native DOM and full source records
stay private. After completion, audit/export only safe review evidence:

```sh
python -m tools.audit_controlled_collection --run data/new-review-run --evidence evidence/new-review-run
```

Report accepted products, rejected responses, exceptions and excluded listing cards separately.
A validated506product sample does not prove full category coverage, stable transport, complete
repeated collection, genuine offers or Azure execution. Production full-crawl entrypoint remains
separate; this entrypoint produces review evidence, without changing production output pointers.


## Interruption and resume

Use the exact same plan and unchanged collection code/settings before the original runtime expires:

```sh
python controlled_collection.py --plan evidence/controlled-skip-invalid-20261025/plan.json --output data/new-review-run --resume
```

The atomic checkpoint retains committed records and pending products/pages. Resume opens a fresh
verified store session, preserves cumulative request/body/runtime limits and capture numbering,
and retries only unfinished work. Changed code/settings or a completed attempt reject resume.
Do not delete the checkpoint, source ledger or captures. One process lock prevents concurrent
writers. Original runtime includes downtime; this bounded tool does not resume expired runs.

Reproduce the small live recovery check once with a fresh output folder:

```sh
python -m tools.run_controlled_recovery --plan evidence/step8-controlled-recovery-20261026/plan.json --output data/new-recovery-run
```

This intentionally kills only its selected collector and browser children. Target3, one category,
12product/control Fetches,2listing Fetches,600seconds total. It does not run a full crawl.
See evidence/step8-controlled-recovery-20261026/RESULTS.md for actual proof and limits.
