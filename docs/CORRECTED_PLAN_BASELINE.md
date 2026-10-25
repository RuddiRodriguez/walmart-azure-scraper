# Corrected plan: step 1 baseline freeze

This step freezes evidence and source. It does not complete the outstanding client requirements.
No collector code/configuration was changed, and no new live or offline acceptance test was run.

## Frozen references

- Source HEAD before inventory:9b7f4ca20c9d76c7a68ba1312a558cd7f7e97d11.
- Existing source package:review-20261025-final-v2,80740bca2fe19bf823637a168cccaaae9f20adec.
- Corrected baseline tag:corrected-baseline-20261025.
- 60 source/configuration/dependency/deployment files fingerprinted; all match the frozen package.
- Public package and private evidence bundle hashes match their receipts. Private bundle remains 0600,
  local and unshared. Anonymous public source-tag access returned HTTP 200 at baseline inventory.

Exact hashes,versions,paths and timestamps: evidence/corrected-plan-20261025/step1-baseline.json.
Per-request completion criteria/status: evidence/corrected-plan-20261025/requirements-register.json.

## Dataset boundaries

| Evidence | Records | Allowed interpretation |
|---|---:|---|
| Earlier live demonstration |500 distinct products|Historical; not fresh final-runner coverage|
| Fresh sample C |33|Separate 24October sample|
| Fresh sample D |33|Separate 24October sample; overlaps C|
| Failed broader attempts |32 and 64|Failed runs; never merge into a successful total|
| Matched comparison |6 distinct targets across 6/3/3 session rows|One short A/B comparison; not 12 distinct targets or complete repeated collection|
| Current-code recovery |3|One-category bounded local restart evidence|

## Evidence reuse

All five collector module hashes still match the successful live SIGKILL/resume evidence.
That evidence can be reused for its recorded bounded scope only. Its configuration differs from
current defaults:one request attempt instead of 3, a 25 second timeout instead of 90, and an explicitly
disabled trace flag. Its category CSV contains one Clorox/Household leaf, rather than all 11 parents.
It does not prove default/full-run or Azure recovery. Later code/configuration changes must be
compared against these hashes and scopes before reusing any result.

The default configuration has max_pages=20000. Full uncapped coverage is unproven; hitting a safety
cap must leave the requirement open. Existing diagnostic-20261025-current.json retains an expired
deadline and prior counters. It is historical provenance, not a configuration for a new test.

## Client context and open requirements

Bentonville #100, 406 S Walton Blvd, AR 72712, PICKUP is accepted for bounded demonstration. Response
identifiers and price-bearing context remain mandatory; banner/price agreement alone is insufficient.
Thirty-five complete Fetch-decoded bodies exist privately, but no complete wrong/correct raw pair.
Earlier wrong-store evidence is parsed JSON; redaction drafts are unreviewed. Generated HTTP request
headers were not captured. No site access/consistency is newly tested by this inventory.

Still open:the requested raw pair,reviewed sharing copies,sustained store correctness,real offers,
full uncapped coverage and repeated complete collection. Current local recovery is proved only
for its recorded bounded scope. Azure is outside the permission granted by the latest message.

## Completion rule and next milestone

A requirement becomes verified only when its stated completion evidence exists. Failed,stopped,
inconclusive or merely scheduled attempts leave it open. Historical evidence is reused only where
source/configuration/scope match. Preparing this baseline does not change those statuses.

Step 1 is complete when this snapshot and requirement register are versioned. Step 2 is not started:
next action is a newly configured bounded investigation to capture the actual raw wrong/correct pair.
Existing batching tests showed no advantage; do not repeat them unchanged as a claimed remedy.

Proposed next diagnostic deliverable:26 October 2026, 18:00 CET (UTC+1), Europe/Amsterdam. Scope is
prepared evidence/findings and explicit blockers, not a promise that every requirement will pass.
No execution has been scheduled; no client message or submission has been authorized or sent.
