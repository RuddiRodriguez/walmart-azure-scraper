"""Bounded live store-context diagnostic: one category, no crawl or publication."""
import argparse
import csv
import hashlib
import json
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from browser import open_browser, select_store, navigate, fetch_product
from extract import next_data
from storage import atomic_json, page_url


def product_context(product, store):
    location = product.get('location') or {}
    actual = {'store_id': str((location.get('pickupLocation') or {}).get('storeId') or ''),
              'zip': str(location.get('postalCode') or ''), 'intent': location.get('intent') or ''}
    expected = {'store_id': str(store['id']), 'zip': store['zip'], 'intent': 'PICKUP'}
    return {'product_id': str(product.get('usItemId') or ''), **actual, 'store_matches': actual == expected}


def trace(failure, output):
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = settings['stores'][0]
    target = json.loads(failure.read_text())['current_work']
    category = next(row['URL'] for row in csv.DictReader(Path('config/categories.csv').open())
                    if row['Category (Auto)'] == target['category'])
    urls = [store['canary_urls'][0], target['url']]
    output.mkdir(parents=True, exist_ok=False)
    result = {'mode': 'live targeted diagnostic; no crawl or product publication',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'category': target['category'],
              'category_url': page_url(category), 'expected_store': {'id': store['id'], 'zip': store['zip']},
              'snapshots': [], 'products': [], 'completed_plan': False,
              'privacy': 'Only location-cookie names and change flags logged; no cookie values or session identifiers.',
              'limit': 'One short session cannot establish repeated/full-run reliability or causation.'}
    sb = None
    prior_cookies = None
    started = time.monotonic()

    def log(event, **values):
        row = {'time_utc': datetime.now(timezone.utc).isoformat(), 'event': event, **values}
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(row) + '\n')
        print(json.dumps(row), flush=True)

    def snapshot(stage):
        nonlocal prior_cookies
        cookies = {(c.name, c.domain, c.path): c.value for c in sb.get_all_cookies()
                   if c.name in ['locDataV3', 'locGuestData', 'assortmentStoreId']}
        changed = [] if prior_cookies is None else sorted({key[0] for key in cookies.keys() | prior_cookies.keys()
                                                         if cookies.get(key) != prior_cookies.get(key)})
        prior_cookies = cookies
        soup = BeautifulSoup(sb.get_page_source(), 'html.parser')
        banner = soup.select_one('[data-automation-id="fulfillment-banner"]')
        text = banner.get_text(' ', strip=True) if banner else ''
        soup.clear(decompose=True)
        soup.decompose()
        row = {'stage': stage, 'page_url': sb.get_current_url(), 'banner': text,
               'banner_matches': 'Pickup' in text and store['name'] in text,
               'location_cookie_names': sorted({key[0] for key in cookies}),
               'location_cookies_changed_since_prior_snapshot': changed}
        result['snapshots'].append(row)
        log('context_snapshot', **row)
        atomic_json(output / 'results.json', result)
        return row

    def fetch(stage, url):
        snapshot(stage + '_before_request')
        soup = fetch_product(sb, url, settings, log)
        try:
            html = str(soup)
            source = stage + '.html'
            (output / source).write_text(html)
            product = next_data(soup).get('data', {}).get('product') or {}
            row = {'stage': stage, 'url': url, 'source_sha256': hashlib.sha256(html.encode()).hexdigest(),
                   **product_context(product, store)}
            row['identity_matches'] = row['product_id'] == url.split('?')[0].rstrip('/').split('/')[-1]
        finally:
            soup.clear(decompose=True)
            soup.decompose()
        result['products'].append(row)
        log('product_context', **row)
        snapshot(stage + '_after_request')
        if not row['identity_matches'] or not row['store_matches']:
            raise ValueError('Product identity or store context mismatch at ' + stage)
        time.sleep(settings['delay_seconds'])

    def timeout(*_):
        raise TimeoutError('Diagnostic reached its 180-second limit')

    prior_alarm = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(180)
    try:
        sb = open_browser()
        select_store(sb, store, settings, log, output)
        snapshot('selected_store')
        for index, url in enumerate(urls):
            fetch('before_category_' + str(index), url)
        soup = navigate(sb, page_url(category), settings, log)
        (output / 'category.html').write_text(str(soup))
        soup.clear(decompose=True)
        soup.decompose()
        snapshot('category_loaded')
        for index in range(2):
            sb.scroll_down(900)
            sb.sleep(1)
            snapshot('category_scroll_' + str(index + 1))
        for index, url in enumerate(urls):
            fetch('after_category_' + str(index), url)
        fetch('after_category_target_repeat', target['url'])
        result['completed_plan'] = True
    except Exception as error:
        result['error'] = str(error)
        result['error_type'] = type(error).__name__
        log('diagnostic_stopped', error=str(error), error_type=type(error).__name__)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prior_alarm)
        result['seconds'] = round(time.monotonic() - started, 2)
        atomic_json(output / 'results.json', result)
        if sb:
            sb.quit()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--failure', type=Path, default=Path('evidence/profile-b/failure.json'))
    parser.add_argument('--output', type=Path, required=True, help='New directory under private data/')
    args = parser.parse_args()
    trace(args.failure, args.output)
