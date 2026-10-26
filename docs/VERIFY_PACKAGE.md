# Verify updated review package

Frozen version: `review-20261026-step9`.

- Source/evidence: https://github.com/RuddiRodriguez/walmart-azure-scraper/tree/review-20261026-step9
- Download: https://github.com/RuddiRodriguez/walmart-azure-scraper/archive/refs/tags/review-20261026-step9.zip
- Authoritative commit: `git rev-parse review-20261026-step9^{commit}` after cloning/fetching tags.
- Local prepared ZIP receipt: `evidence/review-package-20261026/receipt.json` on main, recorded after freezing.
  That receipt is deliberately outside its own frozen archive. It records tag/commit and ZIP hash.

The tag freezes current code, instructions, separate actual datasets, logs, safe response/source
metadata, source audit reports and unsent client draft. No release/client message is published.
Current collector matches live recovery source45ba7c4 byte-for-byte. Earlier two506runs used
byte-identical producers e90c5f0/2ff5e20, before recovery support. Scope cannot be transferred.

Extract downloaded ZIP, enter its root, then verify BEFORE regenerating reports:

```sh
python3 - <<'PY_VERIFY'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('evidence/SHA256SUMS.json').read_text())
for name, expected in manifest.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, name
print(len(manifest), 'files verified')
PY_VERIFY
```

GitHub ZIP may have a different outer hash/root directory from the locally prepared `git archive`.
Verify its frozen commit and individual file hashes; local ZIP hash applies only to that ZIP.

Dataset/evidence index:

| Evidence | Location | Proven scope |
|---|---|---|
| First fresh506 | evidence/controlled-skip-invalid-20261025/ | 11parent categories, independent source checks |
| Repeat fresh506 | evidence/controlled-skip-invalid-repeat-20261025/ | Same-code/settings bounded repetition, comparison |
| Current-source recovery3 | evidence/step8-controlled-recovery-20261026/ | One live SIGKILL/resume, one category |
| Earlier500 | evidence/products-500.json | Historical; never merged with new samples |
| Earlier33samples | evidence/final-session-20261024/diagnostic-c/ and repeat-d/ | Separate earlier samples |
| Wrong/correct pair metadata | evidence/controlled-500-20261025/raw-pair-metadata.json and evidence/controlled-500-continuation-20261025/raw-pair-metadata.json | Complete originals private; reviewed sharing pending |

Run/setup/resume: README.md and docs/CONTROLLED_COLLECTION.md. Current status/open requirements:
docs/REVIEW_STATUS.md, docs/ACCEPTANCE.md and evidence/corrected-plan-20261025/requirements-register.json.
Environment for large samples: environment.json/preflight.json in their evidence folders. Recovery
ran in same local project runtime; source hashes/plan and observed controls are recorded separately.

Source audit reports replayed private captured bodies locally before export. Public ZIP contains safe
fields/hashes, not full raw originals or browser sessions. Running audit_controlled_collection.py
requires a matching private run folder: public archive alone cannot repeat raw-body replay.
`review_package.py` audits only historical500; it does not audit the new506datasets.

Rebuild and verify a separate local archive from a Git checkout:

```sh
python freeze_review_package.py --version review-20261026-step9 --output data/new-review-package.zip
```

Archive checker runs offline: ZIP CRC, complete inventory, file hashes, dataset/export consistency
and stored recovery result. This is not fresh live scraping, new source replay or Azure proof.
