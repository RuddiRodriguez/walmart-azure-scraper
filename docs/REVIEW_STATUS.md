# October 23 review package

## Review starting points

- `evidence/products-500.json`: 500 genuine distinct products from the original live collection.
- `evidence/source-records.json`: corresponding captured listing/product evidence, in matching order.
- `evidence/review-audit.json`: fresh offline comparison of the historical data and captured evidence.
- `evidence/collection-logs/`: original collection and enrichment progress logs, including restarts.
- `evidence/FINAL_REPORT.md`: historical collection counts and limitations.
- `evidence/live-smoke/`: earlier packaged-runner live sample of 22 records across 11 categories.
- `evidence/review-live/`: latest local live run, its coverage queue and collection evidence.
- `evidence/review-regression.json`: explicitly synthetic/offline checks of this revision.
- `evidence/SHA256SUMS.json`: file checksums for the review package.
- `README.md`, `docs/OPERATIONS.md`, `deploy/`: local running, recovery and Azure setup instructions.

## Completed versus outstanding

| Requirement | Evidence and exact boundary |
|---|---|
| 500 distinct genuine products | Historical live collection, freshly audited offline. Zero duplicate IDs and URLs. No newly invented or relabeled records. |
| Store and fulfillment | Captures identify Store 100, Bentonville, ZIP 72712, PICKUP and Walmart seller. This remains a trial store until the client confirms assignment. |
| Prices | Historical listing displayed current prices match captured product-detail current prices. Original crawl dates remain unchanged. This does not establish today's prices. |
| All configured parent categories | Historical 500 records and earlier 22-record live sample cover all 11 parents. |
| Full subcategory coverage | Not complete. Coverage queues explicitly distinguish visited and pending URLs. Parent-category representation is not exhaustive coverage. |
| Unavailable-product retention | Revised code retains an explicitly unavailable item only with local pickup and seller evidence, including empty prices where absent. Offline synthetic checks pass. Live unavailable-item retention remains unproven; saved out-of-stock examples often lack local pickup evidence. |
| Interruption recovery | Earlier live page-stage recovery passed. Latest product-stage recovery result is recorded separately once observed. Offline checkpoint close/reopen is also checked, and is not labeled live proof. |
| Deals | Historical sample has ordinary sales. Seven earlier synthetic deal examples exist. Genuine live volume/digital offers remain unproven. Unknown promotions prevent full publication. |
| Azure execution | Not performed. Installation and twice-weekly service/timer files are supplied. No client VM connection or approved administration path supplied. Local execution is not Azure evidence. |
| Repeat full runs | Not complete. Separate short sessions and resumed samples do not establish unattended production reliability. |
| Failed-run protection | Incomplete samples do not publish. Revised failure handling exports partial records and failure details without changing latest successful output. |

## Changes in this revision

1. Removed blanket stock-status exclusion where explicit local pickup attribution remains available.
2. Allowed genuinely missing prices only for evidenced unavailable records, preserving empty strings.
3. Added partial JSON and failure metadata for interrupted/failed runs.
4. Included original collection logs, the supplied technical brief, an independent evidence audit,
   source checksums and an evidence export command that excludes full browser HTML/session state.
5. Kept historical collection, offline regression and fresh live results separate.

These are responses to the supplied reminder and requirements. No private earlier feedback thread
was available to audit, and no comments were visible under our entry #69.

## Deadline and completion estimate

Fresh contest overview on October 23 showed 1 day, 13 hours remaining. Previously saved contest
metadata gives October 24, 2026 at 16:03:08 UTC / 18:03:08 CEST (Europe/Amsterdam). The live platform
countdown is authoritative and should be checked again before any eventual upload.

The completed local portion is packaged now. Full acceptance has no defensible completion date
yet: client store assignment and Azure access are absent, complete category traversal has not been
observed, and genuine qualifying unavailable/deal examples have not been verified. Do not promise
completion before closing or replace those blockers with an invented date. Set a dated estimate
after access is supplied and the first Azure/store acceptance run reveals actual runtime and failures.

## Running and auditing

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python review_package.py
.venv/bin/python check_review_changes.py
.venv/bin/python scrape.py --store 100 --sample 3
```

Chrome must be installed. The first two commands that run Python scripts are offline audits/checks;
the final command makes a fresh local live collection and does not publish production output.
For full collection, omit `--sample 3`. After interruption, rerun the identical command with
`--resume`; do not reuse checkpoints after changing configuration or beyond 48 hours.

No contest submission, comment, message or file upload was authorized for this review work.
