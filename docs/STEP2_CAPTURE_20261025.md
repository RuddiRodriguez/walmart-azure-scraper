# Step 2: capture and bounded session comparison

Prepared capture of complete response-body bytes exposed by browser Fetch, before HTML parsing.
These are content-decoded bytes, not compressed/TLS wire bytes. Originals, hashes, request options,
attempts, response status, safe headers, timing, sequence and redaction drafts stay under ignored data/.
Redaction drafts require manual privacy review before sharing. Browser-generated request headers
are not captured; no cookie values are logged.

The proposed change is fresh browser sessions after three target products, compared with six targets
in one session. Both arms use the same transport, targets and evidence capture. The six-session
comparison repeats each arm twice; it is a diagnostic hypothesis, not a verified store fix.

Limits:36 product/control attempts,8 listing capture requests,8 native category visits,6 sessions,
40 minutes,10 MiB per body,250 MiB original bodies and8 GiB disk reserve. Browser assets and
store-selection UI requests are additional and not separately capped. Paid services/cloud spend:0.

Any wrong/missing store,ZIP or fulfillment evidence invalidates the comparison. One diagnostic
re-fetch can capture a correction without rehabilitating the failed run. Local unavailable products
use existing product validation and keep unknown local prices empty. Production latest.json is never
written by this diagnostic. Old checkpoints require their original code because browser.py changed.

Ten offline synthetic checks passed, including actual capture JavaScript with mocked Fetch,
byte preservation before parsing,HTTP412 stop,request budget,privacy boundaries,wrong/missing
store evidence and unavailable-product retention. Seven existing offline regression scripts and
compilation passed. No live acceptance is claimed by those checks.

Plan-only command:
python -m tools.bounded_store_review --output data/diagnostic-20261025/proposed

Live execution requires --live and a new private output directory. Source and results must remain
versioned separately from the historical500-product demonstration. Azure access remains ungranted.
