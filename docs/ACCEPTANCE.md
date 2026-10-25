# Acceptance record — current controlled collection

Authoritative status:docs/REVIEW_STATUS.md and
evidence/controlled-skip-invalid-20261025/summary.json. Earlier reports retain their original scope.

| Requirement | Evidence | Status |
|---|---|---|
|Actual500+genuine distinct products|Fresh506 JSON, source e90c5f0, independent506 record audit|Passed bounded sample|
|All11required parent categories represented|12 to 80accepted records/category|Passed representation, not full coverage|
|Store/Pickup/price/identity checks|506 source replays; initial/final controls passed|Passed sample checks|
|Reject bad responses and continue|4 no-pickup/7 missing-listing-price rejections; source unchanged midrun|Observed live; store/identity rejection also tested offline|
|Unavailable products retained|35actual local unavailable records with blank local prices|Passed recorded cases|
|Missing values/schema/deduplication|Empty source values preserved; no invented UPC/weight/PPM;0 duplicate IDs/URLs|Passed current schema/sample rules|
|Historical data separated|Historical500/33/67/79/68notmerged into fresh506|Maintained|
|Raw wrong/correct response pair|2 actual complete pairs private; safe hashes/settings/context metadata public|Reviewed sharing bodies/access pending|
|Smallest transport/session remedy|No prevention remedy proven; validation/filtering mitigation implemented|Open|
|Genuine volume/digital offers|0 verified examples|Open|
|Full uncapped category coverage|Bounded routes/queue only; uncertain links/ArtAprons remain|Open|
|Repeated complete collection|Only one successful506 sample in this mode|Open|
|Final-wrapper live recovery|Earlier3-product production-core recovery is separate|Open for this wrapper/scope|
|Current version/instructions|Live source e90c5f0, plan, JSON, safe audit/checksums in repository|Current repo evidence; earlier ZIP historical|
|Environment/request/runtime/cost bounds|Local Python/Chrome; no paid service; actual519product/control+18listing requests,2063.272 seconds|Documented; browser assets additional|
|Azure|No approved access or execution|Open|

No full production acceptance claimed. Private originals/redaction drafts remain unshared.
