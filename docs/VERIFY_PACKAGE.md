# Verify final local evidence package

Frozen version: `review-20261029-final-azure`.

Source and evidence:
https://github.com/RuddiRodriguez/walmart-azure-scraper/tree/review-20261029-final-azure

Download:
https://github.com/RuddiRodriguez/walmart-azure-scraper/archive/refs/tags/review-20261029-final-azure.zip

Resolve the authoritative commit after cloning or fetching tags:

```sh
git rev-parse review-20261029-final-azure^{commit}
```

## Evidence requested after the previous frozen package

Reviewed wrong-store/corrected-response pairs:
https://github.com/RuddiRodriguez/walmart-azure-scraper/tree/review-20261029-final-azure/evidence/response-pairs-reviewed-20261026

Fifteen-event retention trace:
https://github.com/RuddiRodriguez/walmart-azure-scraper/tree/review-20261029-final-azure/evidence/retention-step2-20261026

Bounded506-product interruption/resume:
https://github.com/RuddiRodriguez/walmart-azure-scraper/tree/review-20261029-final-azure/evidence/point3-20261026/recovery-506

Matching bounded506-product repeat:
https://github.com/RuddiRodriguez/walmart-azure-scraper/tree/review-20261029-final-azure/evidence/point3-20261026/repeat-506

Reviewed Azure diagnostics:
https://github.com/RuddiRodriguez/walmart-azure-scraper/tree/review-20261029-final-azure/evidence/azure-sequence-20261027

The pair folder contains privacy-reviewed redacted response copies and exact preserved product,
store,fulfillment and price fields. Complete original decoded bodies remain private with their hashes
and lengths recorded. No credentials,cookies or browser sessions are included.

The retention work is an offline replay of saved live observations:15 rejection events covering12
products. It keeps eligible unavailable products and dated observations,leaves unsupported current
values blank and separates unknown assortment from confirmed unavailability.

The larger recovery used a SIGKILL after100 saved products,then resumed to506. A second independent
bounded run also reached506 with identical producer bytes and settings. Both remain bounded samples,
not full category/subcategory/pagination coverage.

## Verify every file

Run before regenerating reports:

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

Build and verify a local archive:

```sh
python -m tools.freeze_review_package \
  --version review-20261029-final-azure \
  --output data/review-20261029-final-azure.zip
```

The checker verifies ZIP integrity,full file inventory,global and evidence manifests,separate
datasets,reviewed pair count,retention event count and both recovery samples. It performs no live
collection,client message or submission.

Still open: complete category/subcategory/pagination reconciliation. The final checkpoint records
780 pending pages, 229 failed pages and 9 unresolved navigation pages. The offer review found no
qualifying example in its recorded scope. The bounded Azure diagnostics passed the control product
in two regions but encountered an explicit block on the following Art Sets listing.
