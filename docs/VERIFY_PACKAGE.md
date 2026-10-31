# Verify the 1 November offline correction package

Frozen version: `review-20261101-offline-corrections`.

Source and evidence:
https://github.com/RuddiRodriguez/walmart-azure-scraper/tree/review-20261101-offline-corrections

Download:
https://github.com/RuddiRodriguez/walmart-azure-scraper/archive/refs/tags/review-20261101-offline-corrections.zip

Resolve the exact package commit:

```sh
git rev-parse review-20261101-offline-corrections^{commit}
```

## Verify every listed file

```sh
python3 - <<'PY_VERIFY'
import hashlib, json
from pathlib import Path

manifest = json.loads(Path('evidence/SHA256SUMS.json').read_text())
for name, expected in manifest.items():
    actual = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    assert actual == expected, name
print(len(manifest), 'files verified')
PY_VERIFY
```

The manifest deliberately excludes only itself. It includes the store-session result at
`evidence/store-session-recovery-20261030/RESULT.json`.

## Build and verify the frozen archive

```sh
python -m tools.freeze_review_package \
  --version review-20261101-offline-corrections \
  --output data/review-20261101-offline-corrections.zip
```

The checker verifies ZIP integrity, the full archive inventory, every file hash and the recorded
historical datasets. It does not scrape Walmart, contact the client or run Azure.

## Run source and configuration

`evidence/final-package-20261101/RUN_PROVENANCE.json` covers every client-cited run and every
exported coverage batch report. Missing historical source commits are shown as missing rather than
being replaced by a later evidence commit.

## Open work

Full coverage is not complete: 780 pages remain pending, 216 failures are retryable and 18 paths
remain unresolved. No qualifying volume or digital offer was observed. Clean live collection and
larger current-version recovery/repeat remain blocked on a transport that proves Store 100, ZIP
72712 and PICKUP together.
