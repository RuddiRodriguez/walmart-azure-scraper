"""Reparse exported run evidence and compare it with the delivered JSON, offline."""
import argparse
import json
from pathlib import Path
from bs4 import BeautifulSoup
from extract import product_record
from validate import validate


def audit(folder):
    settings = json.loads(Path('config/stores.json').read_text())
    store = settings['stores'][0]
    product_file = folder / 'products.json'
    if not product_file.exists():
        product_file = folder / 'products.partial.json'
    rows = json.loads(product_file.read_text())
    sources = {x['candidate']['item_id']: x for x in json.loads((folder / 'source-records.json').read_text())}
    mismatches = []
    unavailable = set()
    for row in rows:
        key = row['url'].split('?')[0].rstrip('/').split('/')[-1]
        source = sources.get(key)
        if source is None:
            mismatches.append({'id': key, 'error': 'Missing product source'})
            continue
        soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
        soup.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {
            'product': source['product'], 'idml': {'specifications': source.get('specifications')}}}}}})
        parsed, reason, _ = product_record(source['candidate'], soup, store, settings['private_labels'], row['store_logo'])
        if parsed is None:
            mismatches.append({'id': key, 'error': reason})
            continue
        if reason == 'retained_unavailable':
            unavailable.add(row['url'])
        differences = [field for field in row if field != 'crawl_date' and row[field] != parsed[field]]
        if differences:
            mismatches.append({'id': key, 'fields': differences})
    categories = list({row['category'] for row in rows})
    report = validate(rows, categories, store, {**settings, 'minimum_records': 1}, 0, 0, 0, unavailable_urls=unavailable)
    result = {'mode': 'offline replay of this run source evidence; not a new live collection', 'records': len(rows),
              'passed': report['passed'] and not mismatches, 'validation': report, 'source_mismatches': mismatches,
              'scope': 'Record correctness only; does not imply full category coverage or production acceptance.'}
    (folder / 'source-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'records': len(rows), 'mismatches': mismatches}))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    audit(parser.parse_args().folder)
