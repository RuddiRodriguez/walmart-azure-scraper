"""One bounded Art Aprons Fetch/native comparison; private captures, no publication."""
import argparse
import asyncio
import hashlib
import json
import os
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from browser import open_browser, select_store, fetch_product
from diagnostic_capture import make_capture, safe_url
from extract import next_data, pickup
from storage import atomic_json
from trace_store_context import product_context


TARGET = 'https://www.walmart.com/browse/arts-crafts-sewing/art-aprons/1334134_5899871_4519281'


def describe_html(html):
    page = BeautifulSoup(html, 'html.parser')
    title = page.title.get_text(' ', strip=True) if page.title else ''
    visible = page.get_text(' ', strip=True)
    result = dict(title_present=bool(title), retailer_data_present=bool(page.select_one('#__NEXT_DATA__')),
                  banner_present=bool(page.select_one('[data-automation-id="fulfillment-banner"]')),
                  visible_text_length=len(visible),
                  challenge_visible=bool(page.select_one('#px-captcha')) or bool(re.search(r'robot or human|access denied|press\s*(?:&|and)\s*hold|verify you are human', title + ' ' + visible, re.I)))
    page.decompose()
    return result


def review(output):
    output = Path(output).absolute()
    if not output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Evidence must stay under data/')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = settings['stores'][0]
    state = dict(started=time.monotonic(), limits=dict(product_requests=1, listing_requests=1, seconds=180),
                 product_requests=0, listing_requests=0, sequence=0, body_bytes=0)
    result = dict(mode='One live Art Aprons comparison; no crawl or publication', started_utc=datetime.now(timezone.utc).isoformat(),
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), snapshots=[], completed=False,
                  limits=state['limits'], native_target_load_limit=1)
    sb = None

    def log(event, **values):
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(event=event, **values)) + '\n')

    def save():
        result['counts'] = {k: state[k] for k in ['product_requests', 'listing_requests', 'sequence', 'body_bytes']}
        result['seconds'] = round(time.monotonic() - state['started'], 3)
        atomic_json(output / 'report.json', result)

    def timeout(*_):
        raise TimeoutError('Art Aprons diagnostic180-second limit')

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(180)
    try:
        sb = open_browser()
        select_store(sb, store, settings, log, output)
        control_url = store['canary_urls'][0]
        control = fetch_product(sb, control_url, settings, capture=make_capture(output / 'captures', 'art', state))
        try:
            product = next_data(control).get('data', {}).get('product') or {}
            if not product_context(product, store)['store_matches'] or str(product.get('usItemId')) != '47428850' or not pickup(product, store) or (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart', 'Walmart.com']:
                raise ValueError('Initial store/identity/pickup control failed')
        finally:
            control.decompose()
        result['initial_control_passed'] = True
        try:
            page = fetch_product(sb, TARGET, settings, capture=make_capture(output / 'captures', 'art', state, 'listing'))
            result['fetch_html'] = describe_html(str(page))
            page.decompose()
        except Exception as error:
            result['fetch_error'] = str(error)
            if any(word in str(error) for word in ['Access blocked', 'Challenge', 'Evidence capture failed']):
                raise
        # No reload: four passive observations of the same native navigation.
        sb.goto(TARGET)
        native_started = time.monotonic()
        for index, offset in enumerate([0, 3, 10, 20]):
            sb.sleep(max(0, offset - (time.monotonic() - native_started)))
            html = sb.get_page_source()
            body = html.encode()
            (output / f'native-{index}.html').write_bytes(body)
            observed = dict(seconds_after_goto=round(time.monotonic() - native_started, 3),
                            url=safe_url(sb.get_current_url()), snapshot_sha256=hashlib.sha256(body).hexdigest(),
                            snapshot_bytes=len(body), snapshot_scope='Serialized native DOM, not original HTTP body', **describe_html(html))
            try:
                expression = '({ready_state:document.readyState, content_type:document.contentType, navigation:performance.getEntriesByType("navigation").map(n=>({response_status:n.responseStatus,redirect_count:n.redirectCount,decoded_body_bytes:n.decodedBodySize,transfer_bytes:n.transferSize}))})'
                observed['browser_timing'] = sb.loop.run_until_complete(asyncio.wait_for(sb.page.evaluate(expression, await_promise=True), timeout=5))
            except Exception as error:
                observed['timing_error_type'] = type(error).__name__
            result['snapshots'].append(observed)
            save()
            if observed['challenge_visible']:
                raise ValueError('Visible challenge; no further interaction')
        result['completed'] = True
    except Exception as error:
        result.update(error=str(error), error_type=type(error).__name__)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
        if sb:
            sb.quit()
        save()
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    review(args.output)
