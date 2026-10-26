"""Recheck the saved 500-record evidence without making network requests."""
import json
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup
from extract import product_record, FIELDS


def replay():
    root = Path('evidence')
    rows = json.loads((root / 'products-500.json').read_text())
    sources = json.loads((root / 'source-records.json').read_text())
    config = json.loads(Path('config/stores.json').read_text())
    store = config['stores'][0]
    errors = []
    for row, source in zip(rows, sources):
        soup = BeautifulSoup('<html><script id="__NEXT_DATA__" type="application/json"></script></html>', 'html.parser')
        soup.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {'product': source['product']}}}}})
        parsed, reason, _ = product_record(source['candidate'], soup, store, config['private_labels'], row['store_logo'])
        if not parsed:
            errors.append({'item_id': source['candidate']['item_id'], 'reason': reason})
        elif list(parsed) != FIELDS:
            errors.append({'item_id': source['candidate']['item_id'], 'reason': 'schema'})
        elif any(parsed[k] != row[k] for k in ['upc', 'regular_price', 'sale_price', 'ppm', 'url', 'image_url']):
            errors.append({'item_id': source['candidate']['item_id'], 'reason': 'source_field_mismatch'})
    result = {'mode': 'offline replay of captured live responses; not a fresh crawl', 'records': len(rows),
              'errors': errors, 'passed': len(rows) == len(sources) == 500 and not errors,
              'categories': dict(Counter(r['category'] for r in rows))}
    (root / 'replay-report.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    replay()
