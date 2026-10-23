"""Fresh browser spot checks: compare saved records with visible product-page prices."""
import argparse
import hashlib
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

from browser import open_browser, select_store, navigate, verify_banner, canary_check
from extract import next_data, money, pickup
from storage import atomic_json


def check(products, output):
    settings = json.loads(Path('config/stores.json').read_text())
    store = settings['stores'][0]
    rows = json.loads(products.read_text())
    rng = random.Random(20261023)
    selected = [rng.choice([row for row in rows if row['category'] == category]) for category in sorted({row['category'] for row in rows})]
    output.mkdir(parents=True, exist_ok=True)
    def log(event, **values):
        entry = {'time': datetime.now(timezone.utc).isoformat(), 'event': event, **values}
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(entry) + '\n')
        print(json.dumps(entry), flush=True)
    sb = None
    checks = []
    try:
        sb = open_browser()
        select_store(sb, store, settings, log, output)
        canary_check(sb, store, settings)
        for row in selected:
            key = row['url'].split('?')[0].rstrip('/').split('/')[-1]
            soup = navigate(sb, row['url'], settings, log)
            verify_banner(soup, store)
            product = next_data(soup).get('data', {}).get('product') or {}
            node = soup.select_one('[data-seo-id="hero-price"]')
            visible = node.get_text(' ', strip=True) if node else ''
            match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{1,2})?)', visible)
            observed = money(match.group(1).replace(',', '')) if match else ''
            current = money(((product.get('priceInfo') or {}).get('currentPrice') or {}).get('price'))
            location = product.get('location') or {}
            context_ok = (str(product.get('usItemId')) == key and location.get('intent') == 'PICKUP'
                          and str((location.get('pickupLocation') or {}).get('storeId')) == str(store['id'])
                          and str(location.get('postalCode')) == store['zip'] and pickup(product, store)
                          and (product.get('sellerName') or product.get('sellerDisplayName')) in ['Walmart', 'Walmart.com'])
            ppm = soup.select_one('[data-seo-id="hero-unit-price"]')
            checks.append({'id': key, 'category': row['category'], 'url': row['url'], 'checked_utc': datetime.now(timezone.utc).isoformat(),
                           'saved_crawl_date': row['crawl_date'], 'saved_current_price': row['sale_price'] or row['regular_price'],
                           'visible_price_text': visible, 'visible_current_price': observed, 'response_current_price': current,
                           'visible_matches_response': bool(observed) and observed == current,
                           'saved_price_still_current': bool(observed) and observed == (row['sale_price'] or row['regular_price']),
                           'identity_store_seller_pickup_match': context_ok,
                           'saved_upc': row['upc'], 'observed_upc': str(product.get('upc') or ''),
                           'saved_listing_ppm': row['ppm'], 'observed_detail_ppm': ppm.get_text(' ', strip=True) if ppm else '',
                           'local_page_sha256': hashlib.sha256(str(soup).encode()).hexdigest()})
            sb.save_screenshot(str(output / (key + '.png')))
            atomic_json(output / 'checks.json', checks)
            log('spot_check', id=key, visible_price=observed, saved_price_matches=checks[-1]['saved_price_still_current'], context_ok=context_ok)
            if not context_ok:
                raise ValueError('Fresh spot-check location, seller or availability changed; review required')
        canary_check(sb, store, settings)
        atomic_json(output / 'summary.json', {'mode': 'fresh live browser product-page checks, one randomly selected record per represented category',
                    'seed': 20261023, 'checked': len(checks), 'context_checks_passed': all(c['identity_store_seller_pickup_match'] for c in checks),
                    'visible_response_prices_match': all(c['visible_matches_response'] for c in checks),
                    'saved_prices_still_current': sum(c['saved_price_still_current'] for c in checks),
                    'limit': 'Prices and availability can change after collection. Product-page PPM may use a different displayed unit from listing PPM. Not a full catalog rerun.'})
    except BaseException as error:
        atomic_json(output / 'failure.json', {'error': str(error), 'type': type(error).__name__, 'checked': len(checks)})
        raise
    finally:
        if sb:
            sb.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('products', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    check(args.products, args.output)
