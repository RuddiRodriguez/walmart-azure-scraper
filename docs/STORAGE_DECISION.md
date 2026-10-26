# Storage decision — user pause,26October2026

Point3 is paused explicitly by the user. USER_PAUSED prevents coordinator and walker startup;
30minute reports must not restart it when free space improves. Existing execution/page limits
are not reset. No backup is stopped,reconfigured,ejected or excluded from backup.

## Decision

The SD_Card_3 copy failed with a write I/O error before a complete folder verified. All original
local evidence remained intact. Do not treat that partial SD copy as a reliable backup.

User approved a separate folder on CODEX:
`/Volumes/CODEX/Walmart_Scraper_Private_Evidence`.
This is separate from existing Codex-Mac-Backup. No files in existing backups are modified.

Relocate the project's private data directory only after full copy/hash verification. Keep the
repository's data path as a link,so existing audit/checkpoint paths remain usable. Relocation is
one primary copy,not an independent second backup. CODEX must stay mounted for access. Both raw
responses and native snapshots remain private; no raw bodies/sessions are added to GitHub.

## Cleanup

Remove only untouched automatically generated redaction-draft.html files after verifying matching
complete original body hashes/length metadata and original draft hashes. Approved reviewed
.redacted.html sharing files,original bodies,JSON datasets,native snapshots,logs and checkpoints
remain. Full draft regeneration uses original response bytes and the recorded source version.
Private cleanup receipt lists each removed draft and its preserved original hash.

Remove cache directories from the closed historical dedicated browser profile; keep cookies,
profile identity and evidence. Git metadata was only135MiB,so deleting history or rewriting the
public repository would not solve this pressure. Do not delete old source evidence merely for age.

## Capacity and blocker

Before cleanup,private project data used about9.6GiB. Approximately2.56GiB consisted of regenerable
unreviewed redaction drafts. Internal free space fluctuated between5and9GiB while unrelated system
activity continued; scraper's8GiB safety reserve remains. CODEX had about127GiB available at decision.

Actual verified relocation size and free-space readings are recorded in
`evidence/storage-decision-20261026/relocation-summary.json` after completion,not inferred from copy
progress. If verification or external writes fail,original local evidence is not removed. A separate
external-space reserve remains enforced. No promise of unlimited storage or automatic resumption.

## Verification

`tools/check_archive_evidence.py` uses synthetic files and mocked mount availability. It verifies hash
preservation,path links,receipts,idempotency,failed-copy preservation and missing-drive/space guards.
Actual data-copy verification remains separately recorded. Existing backup jobs are untouched.
