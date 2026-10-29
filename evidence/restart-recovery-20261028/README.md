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

## Storage recovery on 29 October

Disk Utility First Aid was run only against the CODEX APFS volume. It reported an invalid object map and exit code 8, and stated that the volume could not be repaired. The BACKUP volume was not modified.

The verified recovered queue was copied to internal Mac storage and passed SQLite integrity checking before collection resumed. The scraper keeps CODEX as its default storage; the internal continuation uses explicit environment variables.
