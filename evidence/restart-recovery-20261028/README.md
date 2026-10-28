# Restart recovery

The computer restarted while the coverage queue was active. The queue database could not be opened afterward.

Recovery procedure:

- Preserved the malformed database without modifying it.
- Recovered a new database locally with SQLite recovery.
- Verified the recovered database with `PRAGMA integrity_check`.
- Continued from recovered queue state instead of starting coverage again.

Recovered queue state:

- Reviewed: 3,523
- Pending: 1,092
- Failed: 166
- Navigation scope unresolved: 9
- Cross-link excluded: 137
- Outside scope: 1

The recovered state includes committed page work completed after the last saved status snapshot and before the restart.
