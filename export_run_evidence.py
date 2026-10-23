"""Export review evidence from a local run, excluding browser session state and full HTML."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path


PRODUCT_FIELDS = 'usItemId name upc brand sellerName sellerDisplayName availabilityStatus priceInfo location fulfillmentSummary promoData promoDiscount'.split()


def export(run, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in ['products.json', 'report.json', 'products.partial.json', 'failure.json', 'events.jsonl', 'selected-store.png']:
        if (run / name).exists():
            shutil.copy2(run / name, destination / name)
    sources = []
    for path in sorted((run / 'sources').glob('*.json')):
        source = json.loads(path.read_text())
        product = source.get('product') or {}
        sources.append({'candidate': source['candidate'],
                        'product': {key: product.get(key) for key in PRODUCT_FIELDS},
                        'specifications': source.get('specifications'), 'reason': source.get('reason')})
    (destination / 'source-records.json').write_text(json.dumps(sources, indent=2) + '\n')
    db = sqlite3.connect(f'file:{run / "checkpoint.sqlite"}?mode=ro', uri=True)
    coverage = [{'category': c, 'url': u, 'status': s, 'raw_count': r, 'local_count': n}
                for c, u, s, r, n in db.execute('SELECT category,url,status,raw_count,local_count FROM pages ORDER BY category,url')]
    db.close()
    (destination / 'coverage.json').write_text(json.dumps(coverage, indent=2) + '\n')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (run / 'sources').glob('*.html')}
    (destination / 'local-html-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(f'Exported {len(sources)} product responses and {len(coverage)} queued/completed pages')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    export(args.run, args.destination)
