"""Replay both 132-product datasets and report package-size-only changes."""
import json
from pathlib import Path

from bs4 import BeautifulSoup

from extract import product_record


RUNS = ['latest-large-recovery-20261027', 'latest-large-repeat-20261027']


def replay(folder, store, settings):
    rows = json.loads((folder / 'products.json').read_text())
    sources = {source['candidate']['item_id']: source
               for source in json.loads((folder / 'source-records.json').read_text())}
    changes = []
    for row in rows:
        product_id = row['url'].split('?')[0].rstrip('/').split('/')[-1]
        source = sources[product_id]
        soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
        soup.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {
            'product': source['product'],
            'idml': {'specifications': source.get('specifications') or []},
        }}}}})
        parsed, reason, _ = product_record(
            source['candidate'], soup, store, settings['private_labels'], row['store_logo'])
        assert parsed is not None, (product_id, reason)
        changed_fields = [field for field in row
                          if field != 'crawl_date' and row[field] != parsed[field]]
        assert set(changed_fields) <= {'weight'}, (product_id, changed_fields)
        if changed_fields:
            changes.append({
                'product_id': product_id,
                'title': row['product_title'],
                'previous_weight': row['weight'],
                'replayed_weight': parsed['weight'],
            })
    return {
        'records_replayed': len(rows),
        'changed_records': len(changes),
        'changed_fields': ['weight'] if changes else [],
        'changes': changes,
    }


def check():
    settings = json.loads(Path('config/stores.json').read_text())
    store = settings['stores'][0]
    results = {name: replay(Path('evidence') / name, store, settings) for name in RUNS}
    assert all(result['records_replayed'] == 132 for result in results.values())
    result = {
        'mode': 'Offline replay of two historical 132-product datasets; no network or new collection',
        'passed': True,
        'limits': [
            'Historical products and source records are not rewritten.',
            'This proves parser behavior only, not fresh collection or clean-run publication.',
        ],
        'runs': results,
    }
    output = Path('evidence/package-size-replay-20261031.json')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({
        'passed': result['passed'],
        'runs': {name: {
            'records_replayed': value['records_replayed'],
            'changed_records': value['changed_records'],
            'changed_fields': value['changed_fields'],
        } for name, value in results.items()},
    }))


if __name__ == '__main__':
    check()
