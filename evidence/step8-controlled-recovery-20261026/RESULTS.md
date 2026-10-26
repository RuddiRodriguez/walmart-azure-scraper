# Step 8: current collector interruption and resume

Live source: 45ba7c47c0415981c330e911abefa40d0a183be5.
One Art Supplies sample, target three products. SIGKILL after one committed product,
while the next product request was recorded. One manual resume using unchanged code/settings.
Completed in 90.378 seconds including restart, within original 600-second limit.

All 11 recovery/evidence checks passed. Saved record unchanged; committed product not fetched
again; interrupted product retried once and committed once. Three distinct accepted records;
no duplicate commits. Original captured bodies unchanged. Fresh resume control passed Store100,
ZIP72712, PICKUP. Cumulative counts: seven product/control requests, one listing request,
eight capture sequence entries and 4,348,416 original body bytes. Changed settings rejected
before opening browser. Existing 11 synthetic orchestration checks passed separately.

Independent offline source audit passed three actual live row replays, seven complete response
body hashes and one native snapshot hash. The interrupted request has metadata but no complete
response body; it is not counted as a collected product. No failures or invalid product responses
observed in this small sample. No unavailable products occurred; earlier unavailable cases remain
separate proof. Remaining 34 candidates and 13 page links were left unvisited at sample limit.

This proves bounded recovery with current collector, not full-catalog recovery, every crash window,
or 500-record repetition on the changed source. Earlier two 506-record runs remain tied to their
original identical producer code. Full coverage, offers, prevention of upstream drift, privacy-reviewed
pair sharing, refreshed frozen package and Azure proof remain open. Nothing sent to client.
Raw bodies, checkpoint/session details and native HTML remain private under ignored data/.
