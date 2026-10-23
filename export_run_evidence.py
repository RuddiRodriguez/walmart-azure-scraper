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
    for name in ['products.json', 'report.json', 'products.partial.json', 'failure.json', 'events.jsonl', 'selected-store.png', 'hard-stop.json', 'hard-recovery.json', 'hard-stop-between-products.json', 'selected-store.json']:
        if (run / name).exists():
            shutil.copy2(run / name, destination / name)
    sources = []
    for path in sorted((run / 'sources').glob('*.json')):
        source = json.loads(path.read_text())
        if not isinstance(source, dict) or 'candidate' not in source:
            continue
        product = source.get('product') or {}
        sources.append({'candidate': source['candidate'],
                        'product': {key: product.get(key) for key in PRODUCT_FIELDS},
                        'specifications': source.get('specifications'), 'reason': source.get('reason')})
    (destination / 'source-records.json').write_text(json.dumps(sources, indent=2) + '\n')
    db = sqlite3.connect(f'file:{run / "checkpoint.sqlite"}?mode=ro', uri=True)
    coverage = [{'category': c, 'url': u, 'status': s, 'raw_count': r, 'local_count': n}
                for c, u, s, r, n in db.execute('SELECT category,url,status,raw_count,local_count FROM pages ORDER BY category,url')]
    candidates = [{'id': key, 'category': json.loads(data)['category'], 'url': json.loads(data)['url'], 'status': status, 'reason': reason}
                  for key, data, status, reason in db.execute('SELECT id,data,status,reason FROM candidates ORDER BY id')]
    (destination / 'candidate-status.json').write_text(json.dumps(candidates, indent=2) + '\n')
    db.close()
    events = [json.loads(line) for line in (run / 'events.jsonl').read_text().splitlines()]
    for page in coverage:
        matching = [e for e in events if e.get('url') == page['url']]
        page['attempts'] = sum(e['event'] == 'page_started' for e in matching)
        page['load_errors'] = [e for e in matching if e['event'] == 'retry']
        failures = [e for e in events if e['event'] == 'stopped' and e.get('current_work', {}).get('url') == page['url']]
        if page['status'] == 'pending' and failures:
            page['status'] = 'blocked_or_failed'
            page['failure'] = failures[-1]['error']
    for suffix, name in [('links', 'link-decisions.json'), ('listing', 'listing-decisions.json')]:
        decisions = [{'source': p.name, 'data': json.loads(p.read_text())} for p in sorted((run / 'sources').glob('*.' + suffix + '.json'))]
        (destination / name).write_text(json.dumps(decisions, indent=2) + '\n')
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
