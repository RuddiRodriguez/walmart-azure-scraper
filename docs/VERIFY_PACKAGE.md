# Verify the review package

Frozen version: review-20261025-final-v2. GitHub tag identifies the complete source/evidence snapshot.
Collector modules match live-tested commit53cb6d94be5fc29eeedd32cd3f75b129d2f2aed4. Current status
and exact scope: docs/REVIEW_STATUS.md and evidence/diagnostic-20261025/FINAL_STATUS.json.

After downloading/extracting the source ZIP, enter its root folder and verify file hashes before
running scripts that regenerate reports:

```bash
python3 - <<'PY_VERIFY'
import hashlib, json
from pathlib import Path
checksums = json.loads(Path('evidence/SHA256SUMS.json').read_text())
for filename, expected in checksums.items():
    assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == expected, filename
print(len(checksums), 'files match the frozen manifest')
PY_VERIFY
```

The local prepared ZIP receipt records that archive's SHA256. GitHub's automatically generated
ZIP can have a different outer archive hash/prefix while containing identical versioned files.
Verify the tag/commit and file manifest; do not compare the GitHub-generated ZIP against a hash
that belongs to the separately prepared local archive.

README.md contains setup/sample/full/resume commands. Install requirements-review.txt for review
helpers and optional video rendering. Re-audit the historical dataset with python review_package.py;
this updates the audit timestamp and checksum file. It does not perform fresh live collection.

The recorded walkthrough shows actual local/offline command output and saved live evidence.
It is not footage of a fresh full collection or Azure deployment.

Complete raw response bodies/redaction drafts are excluded from the public ZIP and retained in a
separate local private bundle. That bundle is not sent/uploaded, and its drafts need manual privacy
review. Earlier wrong-store JSON and corrected serialized HTML are clearly labeled legacy processed
evidence. They are not a complete raw wrong/correct pair.
