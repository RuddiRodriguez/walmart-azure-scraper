# Why the coverage queue grows

Offline queue snapshot and900verified stored listing bodies inspected. No duplicate category/page
identities and no identical non-sponsored product sets returned for different page numbers were
found. Pagination ranged1–11; it was not generating unbounded page numbers. Most pending work was
new category first pages(1864),not pagination(295),at the audit snapshot. Counts are dated snapshots
while the preserved live batch finishes; see summary.json rather than treating them as current totals.

This is real taxonomy expansion,not evidence of an infinite loop. Different URL/parent link records
are not different queued jobs:queue identity is required category + retailer leaf category ID + page.
Campaign/brand/navigation links with missing ancestry remain separate scope-review work; their
presence in the observed-link ledger does not establish requested category coverage.

Safeguards added without pruning valid required categories:

- Positive numeric page numbers normalized,so01and1cannot create different jobs.
- Repeated full non-sponsored listing item set on a different page stops that pagination branch
  and records a gap. It never marks the branch complete. Empty sets do not trigger a false loop.
- Retailer response page,category identifier,ancestry,store andPickup checks remain mandatory.
- Confirmed category work takes priority over uncertain scope reviews; existing positive scope
  proofs promote matching aliases. Unverified navigation pages cannot spawn an unrelated crawl.
- Per-batch new identities and already-known link counters make expansion measurable.
- Restart retains ORIGINAL12-hour deadline and2000-attempt limit. Current in-flight batch finishes
  before the updated worker adopts it; evidence-export retry does not count it twice.

Ten queue/fingerprint tests andsix coordinator restart/budget tests passed offline. No claim that
full category coverage or genuine promotional examples are complete. Existing506collection source
and required schema/PPM fields remain unchanged. Private raw bodies/session data are not published.
