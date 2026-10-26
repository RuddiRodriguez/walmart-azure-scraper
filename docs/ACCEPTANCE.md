# Acceptance record — current controlled collection and repeat

Current evidence: docs/REVIEW_STATUS.md and
evidence/controlled-skip-invalid-repeat-20261025/summary.json plus comparison.json.
Earlier reports retain their original dates, versions and scopes.

| Requirement | Evidence | Status |
|---|---|---|
| Actual 500+ genuine distinct products | Two separate 506-record JSON files; 506 source replays each | Passed bounded samples |
| All 11 required parent categories represented | Both samples include every required category | Passed representation, not full coverage |
| Store/Pickup/identity/price validation | Every accepted record source-audited; both runs' controls passed | Passed sample checks |
| Reject invalid responses and continue | First: 4 no-pickup, 7 missing listing price. Repeat: 2 wrong-store, 4 no-pickup | Observed live; rejected rows never inserted/re-fetched |
| Unavailable retention | 35 local unavailable records in each sample; blank local prices preserved | Passed recorded cases |
| Schema/missing fields/duplicates | Missing source values stay blank; zero duplicate IDs/URLs in either sample | Passed current sample rules |
| Bounded repeat with unchanged collection code/settings | Producer hashes, plan bytes, configs and versions matched | Passed requested bounded repeat |
| Repeated full uncapped collection | Scope and queue exhaustion not established | Open |
| Raw wrong/correct response pair | Two actual complete pairs private; safe hashes/settings metadata public | Reviewed sharing bodies/access pending |
| Transport/session prevention remedy | Rejection/filtering mitigation works; cause/prevention unproven | Open |
| Genuine volume/digital offers | Zero verified examples | Open |
| Full uncapped category coverage | Uncertain landing links/ArtAprons and pending queues remain | Open |
| Current-wrapper live recovery | Source45ba7c4: three genuine records, SIGKILL/resume,11checks plus3source replays passed | Passed bounded one-category case; full-catalog recovery unproven |
| Version/instructions/package | Current source/JSON/audits/plan/comparison in repo; older frozen ZIP historical | Repo evidence current; refreshed package pending |
| Request/runtime/cost bounds | Both bounded runs within identical caps; no paid service, assets additional | Documented |
| Azure | No approved access or execution | Open |

No full production acceptance claimed. Complete original bodies, native DOM and unreviewed redaction
copies remain private. No client messages or submissions sent.
