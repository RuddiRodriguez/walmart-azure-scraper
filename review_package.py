"""Build an offline evidence audit and checksums. Does not scrape or submit anything."""
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from extract import FIELDS, money, pickup
from validate import validate


def build():
    root = Path(__file__).parent
    evidence = root / 'evidence'
    rows = json.loads((evidence / 'products-500.json').read_text())
    sources = json.loads((evidence / 'source-records.json').read_text())
    settings = json.loads((root / 'config/stores.json').read_text())
    store = settings['stores'][0]
    categories = [r['Category (Auto)'] for r in csv.DictReader((root / 'config/categories.csv').open())]
    ids = [s['candidate']['item_id'] for s in sources]
    errors = []
    validation = validate(rows, categories, store, settings, 0, 0, 0)
    errors.extend(validation['errors'])
    if len(rows) != len(sources) or len(rows) < 500:
        errors.append('Fewer than 500 records or source count mismatch')
    for index, (row, source) in enumerate(zip(rows, sources)):
        candidate, product = source['candidate'], source['product']
        location = product.get('location') or {}
        current = (product.get('priceInfo') or {}).get('currentPrice') or {}
        displayed = re.search(r'(?:Price Now|Price) \$(\d+(?:\.\d{1,2})?)', candidate['price_text'])
        checks = {
            'schema': list(row) == FIELDS and all(isinstance(v, str) for v in row.values()),
            'identity': candidate['item_id'] == str(product.get('usItemId')),
            'url': row['url'] == candidate['url'],
            'store': location.get('intent') == 'PICKUP' and str((location.get('pickupLocation') or {}).get('storeId')) == str(store['id']) and str(location.get('postalCode') or '') == store['zip'] and pickup(product, store),
            'seller': (product.get('sellerName') or product.get('sellerDisplayName')) in ['Walmart', 'Walmart.com'],
            'price': bool(displayed) and money(current.get('price')) == money(displayed.group(1)) == (row['sale_price'] or row['regular_price']),
            'upc': row['upc'] == str(product.get('upc') or ''),
            'ppm': not row['ppm'] or row['ppm'] in candidate['price_text'],
            'downstream_fields': row['gupc'] == row['unit_price'] == '',
            'not_sponsored': not candidate['item'].get('isSponsoredFlag') and not candidate['item'].get('sponsoredProduct') and 'Sponsored' not in candidate['text'],
        }
        errors.extend({'record': index, 'id': candidate['item_id'], 'check': key} for key, passed in checks.items() if not passed)
    counts = Counter(r['category'] for r in rows)
    duplicates = {'ids': len(ids) - len(set(ids)), 'urls': len(rows) - len({r['url'] for r in rows})}
    if any(duplicates.values()) or set(categories) - set(counts):
        errors.append('Duplicate identity or missing parent category')
    report = {
        'audit_time_utc': datetime.now(timezone.utc).isoformat(),
        'mode': 'offline audit of historical live captures; not a fresh collection',
        'audit_base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'audited_code_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                               for name in ['extract.py', 'scrape.py', 'storage.py', 'validate.py', 'browser.py']},
        'passed': not errors, 'records': len(rows), 'sources': len(sources),
        'duplicates': duplicates, 'category_counts': dict(counts),
        'collection_dates': sorted({r['crawl_date'] for r in rows}),
        'field_nonempty_counts': {f: sum(bool(r[f]) for r in rows) for f in FIELDS},
        'errors': errors,
        'limits': ['Store 100 is a trial store; assignment unconfirmed.',
                   'Parent representation is not full subcategory coverage.',
                   'Historical multi-pass logs do not establish uninterrupted runtime.',
                   'Azure execution and genuine live volume/digital offers remain unproven.'],
    }
    (evidence / 'review-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    files = subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines()
    manifest = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files
                if (root / name).is_file() and name != 'evidence/SHA256SUMS.json'}
    (evidence / 'SHA256SUMS.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'records': len(rows), 'duplicates': duplicates, 'errors': errors}))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    build()
