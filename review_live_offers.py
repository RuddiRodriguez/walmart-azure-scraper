"""Inspect two bounded local-pickup offer searches. Never publishes product output."""
import argparse
import csv
import json
import os
import re
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from browser import open_browser, select_store, navigate, verify_banner, fetch_product
from diagnostic_capture import make_capture, safe_url
from extract import listing_candidates, next_data, pickup, product_record, promotion_fields
from storage import atomic_json
from trace_store_context import product_context


def review(output):
    output = Path(output).resolve()
    if not output.is_relative_to(Path('data').resolve()):
        raise ValueError('Offer evidence must stay under ignored data/')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = settings['stores'][0]
    with Path('config/categories.csv').open() as source:
        categories = [r['Category (Auto)'] for r in csv.DictReader(source)]
    state = {'started': time.monotonic(), 'limits': {'product_requests': 8, 'listing_requests': 2, 'seconds': 600},
             'product_requests': 0, 'listing_requests': 0, 'sequence': 0, 'body_bytes': 0}
    result = {'mode': 'bounded live offer inspection; not a catalog run',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'queries': [], 'products': [],
              'verified_examples': [], 'completed': False, 'paid_services_used': False}
    sb = None

    def save():
        result['counts'] = {k: state[k] for k in ['product_requests', 'listing_requests', 'sequence', 'body_bytes']}
        result['seconds'] = round(time.monotonic() - state['started'], 3)
        atomic_json(output / 'report.json', result)

    def log(event, **values):
        with (output / 'events.jsonl').open('a') as target:
            target.write(json.dumps({'time_utc': datetime.now(timezone.utc).isoformat(), 'event': event, **values}) + '\n')

    def control():
        url = store['canary_urls'][0]
        page = fetch_product(sb, url, settings, capture=make_capture(output / 'captures', 'offers', state))
        try:
            product = next_data(page).get('data', {}).get('product') or {}
            if (not product_context(product, store)['store_matches'] or not pickup(product, store)
                    or str(product.get('usItemId')) != url.split('?')[0].rstrip('/').split('/')[-1]
                    or (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart', 'Walmart.com']):
                raise ValueError('Offer control store/identity/seller/pickup failed')
        finally:
            page.decompose()

    def timeout(*_):
        raise TimeoutError('Offer review reached ten-minute limit')

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    try:
        sb = open_browser()
        logo = select_store(sb, store, settings, log, output)
        control()
        for query in ['buy 2 save', 'digital coupon']:
            url = 'https://www.walmart.com/search?' + urlencode({'q': query, 'stores': '100', 'facet': 'fulfillment_method:Pickup'})
            entry = {'query': query, 'url': safe_url(url), 'inspected': 0}
            result['queries'].append(entry)
            page = navigate(sb, url, settings, log)
            verify_banner(page, store)
            page.decompose()
            page = fetch_product(sb, url, settings, capture=make_capture(output / 'captures', 'offers', state, 'listing'))
            try:
                search = next_data(page).get('searchResult') or {}
                props = (search.get('paginationV2') or {}).get('pageProperties') or {}
                entry['listing_context'] = {k: props.get(k) for k in ['stores', 'facet', 'page']}
                if str(props.get('stores') or '') != '100' or 'fulfillment_method:Pickup' not in str(props.get('facet') or ''):
                    raise ValueError('Offer search lacks verified local-pickup source context')
                candidates = {}
                for category in categories:
                    local, _, _ = listing_candidates(page, category, store)
                    for candidate in local:
                        candidates.setdefault(candidate['item_id'], candidate)
                pattern = re.compile(r'\b\d+\s+for\s+\$|\bbuy\s+\d|when you buy|mix or match|must buy|digital coupon|\bclip\b|\bactivate\b', re.I)
                ranked = sorted(candidates.values(), key=lambda c: not bool(pattern.search(c['text'])))
                entry['eligible_candidates'] = len(ranked)
                selected = ranked[:3]
            finally:
                page.decompose()
            for candidate in selected:
                page = fetch_product(sb, candidate['url'], settings, capture=make_capture(output / 'captures', 'offers', state))
                try:
                    record, reason, product = product_record(candidate, page, store, settings['private_labels'], logo)
                    fields, unknown = promotion_fields(product)
                    visible = ' '.join(page.get_text(' ', strip=True).split())
                    descriptions = [fields[k] for k in ['volume_deals_description', 'digital_deals_description'] if fields[k]]
                    description_visible = bool(descriptions) and all(' '.join(d.split()) in visible for d in descriptions)
                    row = {'sequence': state['sequence'], 'query': query, 'candidate_id': candidate['item_id'],
                           **product_context(product, store), 'accepted': record is not None, 'reason': reason,
                           'fields': fields, 'unknown_offer_shapes': unknown,
                           'description_visible_in_response': description_visible,
                           'current_local_price': (record['sale_price'] or record['regular_price']) if record else ''}
                    result['products'].append(row)
                    entry['inspected'] += 1
                    if record and reason != 'retained_unavailable' and not unknown and description_visible:
                        result['verified_examples'].append(row)
                    save()
                finally:
                    page.decompose()
                time.sleep(settings['delay_seconds'])
            save()
        control()
        result['completed'] = True
    except Exception as error:
        result['error'] = str(error)
        result['error_type'] = type(error).__name__
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
        if sb:
            sb.quit()
        save()
    print(json.dumps({'completed': result['completed'], 'examples': len(result['verified_examples']),
                      'counts': result['counts'], 'error': result.get('error')}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if not review(args.output)['completed']:
        raise SystemExit(1)
