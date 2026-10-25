# Step 4 results — 25 October 2026, 18:31 CET

The current collector passed a bounded live interruption/resume test. Genuine volume/digital
offer examples remain unverified after the targeted inspection. No live review process remains
running, and nothing was sent to the client.

## Live recovery

The actual scrape.py process was killed with SIGKILL after one product had been committed,
when the next product attempt started. Its browser children were also terminated. The same
checkpoint resumed with identical source, configuration and category file. Three records
completed successfully; source audits passed for all three.

All seven recovery checks passed: SQLite integrity, saved pages processed once, saved records
retained, saved products completed once, interrupted product initially uncommitted, interrupted
product attempted twice and completed once. Interrupted product: 883632494.

Elapsed review time: 87.422 seconds. Four target attempts plus at most two configured canary
attempts stayed within the 12-product-attempt/15-minute budget. Network packet timing is not
measured; a started attempt does not prove precisely when its request reached Walmart.

Scope: current collector code, one Household Essentials/Clorox category and a three-product
sample. This establishes local recovery for that bounded configuration. It does not establish
full-catalog or Azure recovery. The review used one request attempt and a 25-second request
timeout; source/configuration stayed identical across interruption and resume.

Core source commit: 53cb6d94be5fc29eeedd32cd3f75b129d2f2aed4. All five collector module hashes
still match the tested source. Exact settings, category CSV, source evidence, logs, hard-stop
snapshot and recovery checks are in evidence/diagnostic-20261025/step4-recovery/.

## Live offer inspection

Two Store #100/PICKUP searches: “buy 2 save” and “digital coupon”. Five target checks covered
three distinct products. All five passed local product validation; no recognized qualifying
volume/digital offer description or price was present. The parser reported no unknown offer
shapes for these five responses. Financing/reward offers are not counted as qualifying deals.

The review finished in 62.594 seconds, using seven product/control requests and two listing
capture GETs. This stayed within eight product requests, two searches and ten minutes. Browser
assets and store-selection UI requests are additional and not separately counted. No further
searches were run after this bounded inspection.

Nine complete Fetch-decoded response bodies and redaction drafts remain private; all nine
original-body hashes were verified. Public metadata and selected source context are in
evidence/diagnostic-20261025/step4-offers/. Redaction drafts require privacy review before sharing.

## Status

Historical 500-product JSON and production latest state stayed unchanged. Earlier 33-product
samples, the six-target comparison and this three-product recovery sample remain separate.

Local current-code recovery now has fresh live evidence. Still open: genuine volume/digital
examples, paired raw wrong/correct drift capture, sustained store reliability, full uncapped
coverage, repeated complete collection and Azure execution. Client feedback grants no Azure
access. No paid service, client message or submission was used.
