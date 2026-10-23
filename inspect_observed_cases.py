"""Inspect saved listing pages for genuine unavailable products and offer shapes; offline only."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup
from extract import next_data, pickup


def inspect(folder, destination):
    store = json.loads(Path('config/stores.json').read_text())['stores'][0]
    cases = []
    counts = Counter()
    for path in sorted(folder.glob('*.html')):
        soup = BeautifulSoup(path.read_text(), 'html.parser')
        data = next_data(soup)
        search = data.get('searchResult') or {}
        for stack in search.get('itemStacks', []):
            for item in stack.get('items', []):
                if item.get('__typename') != 'Product':
                    continue
                counts['product_observations'] += 1
                unavailable = item.get('availabilityStatus') in ['OUT_OF_STOCK', 'UNAVAILABLE']
                if unavailable:
                    counts['unavailable_observations'] += 1
                    counts['unavailable_with_local_pickup'] += bool(pickup(item, store))
                if unavailable or item.get('promoData') or item.get('promoDiscount'):
                    cases.append({'source_file': path.name, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                  'id': item.get('usItemId'), 'name': item.get('name'), 'availabilityStatus': item.get('availabilityStatus'),
                                  'sellerName': item.get('sellerName'), 'local_pickup': pickup(item, store),
                                  'fulfillmentSummary': item.get('fulfillmentSummary'), 'priceInfo': item.get('priceInfo'),
                                  'promoData': item.get('promoData'), 'promoDiscount': item.get('promoDiscount')})
    result = {'mode': 'offline inspection of genuine historical saved pages; not a fresh collection', 'counts': dict(counts), 'cases': cases,
              'limit': 'A selected-store banner alone does not attribute a shipping price to local pickup. Missing pickup evidence remains unresolved.'}
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    inspect(args.folder, args.destination)
