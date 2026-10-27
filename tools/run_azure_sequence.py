"""Small Azure-only navigation test. No crawl and no product publication."""
import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from browser import open_browser, select_store, capture_navigation, capture_product_navigation
from diagnostic_capture import make_capture, safe_url
from extract import next_data
from storage import atomic_json, product_url
from trace_store_context import product_context


LISTING_URL = 'https://www.walmart.com/browse/arts-crafts-sewing/art-sets/1334134_5899871_7148292'
BLOCKED_CANDIDATE = 'https://www.walmart.com/ip/FlowArt-Dot-By-Letter-Into-the-Galaxy-Metallic-ink/19476757527?fulfillmentIntent=Pickup&classType=VARIANT'
SECOND_CANDIDATE = 'https://www.walmart.com/ip/Crayola-Imagination-Art-Coloring-Set-115-Pcs-Easter-Basket-Stuffers-Art-Craft-Kit-Coloring-Supplies-Easter-Gifts-for-Kids/878215686?fulfillmentIntent=Pickup&classType=REGULAR'


def page_state(sb, store, output, name):
    html = sb.get_page_source()
    url = sb.get_current_url()
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    banner = soup.select_one('[data-automation-id="fulfillment-banner"]')
    blocked = urlsplit(url).path.startswith('/blocked') or any(
        word in title.lower() for word in ['robot or human', 'access denied', 'captcha'])
    state = {
        'url': safe_url(url),
        'title': title,
        'classification': ('walmart_block_page' if blocked else
                           'normal_page' if title and soup.select_one('#__NEXT_DATA__') else
                           'incomplete_or_unknown_page'),
        'banner_present': bool(banner),
        'banner_matches': bool(banner and 'Pickup' in banner.get_text(' ', strip=True)
                               and store['name'] in banner.get_text(' ', strip=True)),
        'next_data_present': bool(soup.select_one('#__NEXT_DATA__')),
        'html_bytes': len(html.encode()),
        'html_sha256': hashlib.sha256(html.encode()).hexdigest(),
    }
    (output / f'{name}-private.html').write_text(html)
    soup.decompose()
    return state


def product_price(product):
    current = (product.get('priceInfo') or {}).get('currentPrice') or {}
    return {
        'current_price': current.get('price', ''),
        'current_price_unit': current.get('unitPriceDisplayValue', ''),
    }


def run(output):
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = settings['stores'][0]
    control_url = product_url(store['canary_urls'][0])
    state = {
        'started': time.monotonic(),
        'limits': {'product_requests': 4, 'listing_requests': 1, 'seconds': 600},
        'product_requests': 0,
        'listing_requests': 0,
        'sequence': 0,
        'body_bytes': 0,
        'body_limit_bytes': 128 * 2**20,
    }
    result = {
        'mode': 'Bounded Azure navigation sequence; no crawl or publication',
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'expected': {'store_id': str(store['id']), 'zip': store['zip'], 'intent': 'PICKUP'},
        'limits': state['limits'],
        'steps': [],
        'completed': False,
    }
    sb = None

    def save():
        result['counts'] = {key: state[key] for key in ['product_requests', 'listing_requests', 'sequence', 'body_bytes']}
        result['seconds'] = round(time.monotonic() - state['started'], 3)
        atomic_json(output / 'result.json', result)

    def log(event, **values):
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps({'time_utc': datetime.now(timezone.utc).isoformat(), 'event': event, **values}) + '\n')

    def product_step(name, url):
        row = {'name': name, 'requested_url': safe_url(url), 'status': 'started'}
        result['steps'].append(row)
        save()
        page = None
        try:
            page = capture_product_navigation(
                sb, url, settings, log,
                make_capture(output / 'captures', 'azure-sequence', state, 'product'))
            product = next_data(page).get('data', {}).get('product') or {}
            row.update(status='passed', **product_context(product, store), **product_price(product))
            row['identity_matches'] = row['product_id'] == urlsplit(url).path.rstrip('/').split('/')[-1]
            if not row['store_matches'] or not row['identity_matches']:
                row['status'] = 'rejected'
        except Exception as error:
            row.update(status='failed', error_type=type(error).__name__, error=str(error),
                       page=page_state(sb, store, output, name))
        finally:
            if page is not None:
                page.decompose()
            save()
        return row['status'] == 'passed'

    try:
        sb = open_browser()
        try:
            select_store(sb, store, settings, log, output)
            result['store_selection'] = {'status': 'passed'}
        except Exception as error:
            result['store_selection'] = {
                'status': 'failed',
                'error_type': type(error).__name__,
                'error': str(error),
                'page': page_state(sb, store, output, 'store-selection-failure'),
            }
            return result
        if not product_step('control-before-listing', control_url):
            return result
        listing = {'name': 'listing', 'requested_url': safe_url(LISTING_URL), 'status': 'started'}
        result['steps'].append(listing)
        save()
        page = None
        try:
            page, _ = capture_navigation(
                sb, LISTING_URL, settings, log,
                make_capture(output / 'captures', 'azure-sequence', state, 'listing'),
                response_kind='listing')
            listing['status'] = 'passed'
        except Exception as error:
            listing.update(status='failed', error_type=type(error).__name__, error=str(error),
                           page=page_state(sb, store, output, 'listing'))
            return result
        finally:
            if page is not None:
                page.decompose()
            save()
        candidate_passed = product_step('previously-blocked-clean-url', BLOCKED_CANDIDATE)
        if candidate_passed:
            product_step('second-candidate-clean-url', SECOND_CANDIDATE)
        product_step('control-after-candidate', control_url)
        result['completed'] = True
        return result
    finally:
        if sb is not None:
            sb.quit()
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)
