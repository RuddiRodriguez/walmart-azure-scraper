# Step 3 results — 25 October 2026, 17:59 CET

One matched live comparison completed on source 09c92cb7e28ff1cd6bad95f23c1fcc10d7bb23a6.
A six-product session passed; fresh three-product sessions passed the same six targets in the
same order, with matching output prices. All six products had local prices; this sample did not
exercise unavailable-product retention. The seven distinct product identities include the control.

The matched comparison took 164.762 seconds:18 product/control requests,4 listing capture GETs,
4 native category visits and3 browser sessions. Initial stale-target work and a discovery session
bring total step 3 usage to 20 product requests,6 listing GETs,6 native visits and5 browser sessions.
All remained within original 36/8/8/6 request/session limits and original 40 minute wall deadline.
Browser assets and store-selection UI requests are additional and not separately counted.

The initial attempt stopped after 42.21 seconds because a saved target was absent from the current
listing. It accepted 1 target; its records remain separate. Targets were refreshed from actual current
listing responses. To retain the original budget, the second matched repeat was omitted. There is
one completed A/B comparison, not two completed repeats and not twelve distinct target products.

## Evidence and verification

- 26 complete Fetch-decoded response bodies retained privately; all original-body SHA256 hashes verified.
- 20 product response contexts show100/72712/PICKUP; 6 listing responses show100/Pickup.
- No wrong-store response observed. No new paired wrong/correct raw response was captured.
- Request options,attempts,response status,allowed headers,sequence,timing and source identifiers retained.
- Historical 500-product JSON and production latest state remained unchanged.
- Raw originals and redaction drafts stay under ignored data/; drafts require manual privacy review.
- Public evidence contains metadata,selected source fields and accepted rows grouped by session.

See evidence/diagnostic-20261025/step3-results/summary.json,capture-metadata.json,
source-contexts.json,comparison-report.json and accepted-by-session.json.

Both strategies passed this short sample. Session batching has no demonstrated improvement here.
Sustained store correctness,full uncapped coverage,repeated complete collection,paired drift capture,
live offers,final-version live interruption/resume and Azure execution remain outstanding.
No Azure access was granted; no paid service used; no client contact or submission occurred.
Live diagnostic finished; no further test or target refresh is part of step 3.
