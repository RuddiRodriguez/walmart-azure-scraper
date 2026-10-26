"""Offline response-capture/session checks. Synthetic fixtures; no browser or network."""
import asyncio
import base64
import copy
import hashlib
import json
import tempfile
import time
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup

from tools import bounded_store_review as review
from browser import fetch_product
from diagnostic_capture import make_capture, redact_body, safe_url
from storage import atomic_json


def state():
    return {'started': time.monotonic(), 'limits': {'product_requests': 36, 'listing_requests': 8, 'seconds': 2400},
            'product_requests': 0, 'listing_requests': 0, 'sequence': 0, 'body_bytes': 0}


def response(body, status=200):
    return {'status': status, 'url': 'https://www.walmart.com/ip/1?visitor=PRIVATE',
            'html': body.decode('utf-8', errors='replace'), 'body_base64': base64.b64encode(body).decode(),
            'headers': {'cache-status': 'Miss', 'set-cookie': 'PRIVATE'}}


def check():
    checks = []
    Path('data').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir='data') as folder:
        output = Path(folder)
        raw = b'<title>Fixture</title>\r\n<!-- exact spacing -->\xff'
        seen = state()
        capture = make_capture(output / 'bytes', 'A1', seen)
        async def evaluate(*args, **kwargs):
            return response(raw)
        loop = asyncio.new_event_loop()
        sb = SimpleNamespace(loop=loop, page=SimpleNamespace(evaluate=evaluate))
        try:
            with patch('browser.check_html', side_effect=ValueError('synthetic parser failure')):
                try:
                    fetch_product(sb, 'https://www.walmart.com/ip/1?token=PRIVATE',
                                  {'retries': 1, 'max_page_seconds': 1}, capture=capture)
                except ValueError:
                    pass
                else:
                    raise AssertionError('Parser failure suppressed')
        finally:
            loop.close()
        assert (output / 'bytes/A1-001.body').read_bytes() == raw
        meta = json.loads((output / 'bytes/A1-001.json').read_text())
        assert meta['body_sha256'] == hashlib.sha256(raw).hexdigest()
        assert 'PRIVATE' not in json.dumps(meta)
        assert meta['request']['attempt'] == 1
        checks.append('Complete synthetic Fetch bytes retained before parser failure; hash and redacted metadata verified')

        # Execute the actual browser expression against a local mocked Fetch implementation.
        # Node is only an offline verifier; the Python live runner does not depend on it.
        node = shutil.which('node')
        assert node, 'Node required for offline verification of capture JavaScript'
        async def execute_js(expression, **kwargs):
            setup = 'global.fetch=async()=>new Response(Buffer.from(' + json.dumps(base64.b64encode(raw).decode()) + ',"base64"));'
            code = setup + '(' + expression + ').then(r=>process.stdout.write(JSON.stringify(r))).catch(e=>{process.stderr.write(e.message);process.exit(1)});'
            result = subprocess.run([node, '-e', code], capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        loop = asyncio.new_event_loop()
        try:
            page = fetch_product(SimpleNamespace(loop=loop, page=SimpleNamespace(evaluate=execute_js)),
                                 'https://www.walmart.com/ip/1', {'retries': 1, 'max_page_seconds': 2},
                                 capture=make_capture(output / 'javascript', 'JS', state()))
            page.decompose()
        finally:
            loop.close()
        assert (output / 'javascript/JS-001.body').read_bytes() == raw
        checks.append('Actual capture JavaScript executed offline with mocked Fetch; CRLF and invalid UTF8 bytes preserved')

        calls = []
        async def blocked(*args, **kwargs):
            calls.append(1)
            return response(b'<title>Blocked</title>', 412)
        loop = asyncio.new_event_loop()
        try:
            try:
                fetch_product(SimpleNamespace(loop=loop, page=SimpleNamespace(evaluate=blocked)),
                              'https://www.walmart.com/ip/1', {'retries': 3, 'max_page_seconds': 1},
                              capture=make_capture(output / 'blocked', 'A2', state()))
            except ValueError:
                pass
            assert len(calls) == 1 and (output / 'blocked/A2-001.body').exists()
        finally:
            loop.close()
        checks.append('HTTP412 captured then stopped without retry')

        exhausted = state()
        exhausted['product_requests'] = 36
        callback = make_capture(output / 'limit', 'limit', exhausted)
        try:
            callback('request', url='https://www.walmart.com/ip/1')
        except RuntimeError:
            pass
        else:
            raise AssertionError('Request cap ignored')
        checks.append('Request budget stops before network call')
        try:
            make_capture('evidence/unsafe-raw-test', 'test', state())
        except ValueError:
            pass
        else:
            raise AssertionError('Public raw-output path allowed')
        checks.append('Raw evidence output outside ignored data rejected')

        fixture = {'props': {'pageProps': {'initialData': {'data': {'product': {
            'usItemId': '123', 'location': {'postalCode': '72712', 'pickupLocation': {'storeId': '100'}},
            'priceInfo': {'currentPrice': {'price': 6.26}}, 'sessionId': 'SECRET',
            'customer': {'email': 'PRIVATE'}}}}}}}
        html = ('<script>var token="SECRET"</script><input value="SECRET"><script id="__NEXT_DATA__">'
                + json.dumps(fixture) + '</script>').encode()
        redacted = redact_body(html).decode()
        assert 'SECRET' not in redacted and 'PRIVATE' not in redacted
        assert all(v in redacted for v in ['72712', '100', '6.26', '123'])
        assert 'PRIVATE' not in safe_url('https://user:PRIVATE@www.walmart.com/ip/1?token=PRIVATE')
        checks.append('Synthetic redaction removes known secrets while preserving product/store/price identifiers')

        plan = json.loads(Path('config/diagnostic-20261025.json').read_text())
        sessions = review.sessions(plan['cases'])
        assert len(sessions) == 6
        assert len({s['id'] for s in sessions}) == 6
        assert sum(len(s['cases']) + 2 for s in sessions) == 36
        for repeat in [1, 2]:
            a = next(s['cases'] for s in sessions if s['id'] == f'A{repeat}')
            b = [c for s in sessions if s['id'].startswith(f'B{repeat}-') for c in s['cases']]
            assert a == b
        checks.append('Two matched A/B comparisons planned; six fresh sessions and36product/control requests')

        source = json.loads(Path('evidence/source-records.json').read_text())[0]
        store = json.loads(Path('config/stores.json').read_text())['stores'][0]
        candidate = source['candidate']
        latest = output / 'last-good.json'
        latest.write_bytes(b'unchanged last good')
        for mode in ['wrong_store', 'missing_zip', 'unavailable']:
            count = [0]
            def fake_fetch(sb, url, settings, log=None, capture=None):
                count[0] += 1
                product = copy.deepcopy(source['product'])
                product['usItemId'] = url.split('?')[0].rstrip('/').split('/')[-1]
                if count[0] == 3:
                    if mode == 'wrong_store':
                        product['location']['pickupLocation']['storeId'] = '3081'
                    elif mode == 'missing_zip':
                        product['location'].pop('postalCode', None)
                    else:
                        product['fulfillmentSummary'] = []
                        product['fulfillmentOptions'] = [{'type': 'PICKUP', 'locationText': store['name'], 'availabilityStatus': 'OUT_OF_STOCK'}]
                body = ('<title>Synthetic</title><script id="__NEXT_DATA__">' + json.dumps(
                    {'props': {'pageProps': {'initialData': {'data': {'product': product}}}}}) + '</script>').encode()
                capture('request', url=url, attempt=1, settings={'method': 'GET'})
                capture('response', result=response(body), received_utc='synthetic', elapsed_seconds=0)
                return BeautifulSoup(body, 'html.parser')
            one = [{'id': 'A1', 'mode': 'synthetic', 'cases': [{'category': candidate['category'],
                    'listing_url': 'https://www.walmart.com/browse/test/1', 'item_id': candidate['item_id']}]}]
            with patch.multiple(review, open_browser=lambda: SimpleNamespace(quit=lambda: None),
                                select_store=lambda *a: '', fetch_product=fake_fetch,
                                store_snapshot=lambda *a: ({'banner_matches': True}, {}),
                                navigate=lambda *a: BeautifulSoup('<title>Page</title>', 'html.parser'),
                                verify_banner=lambda *a: None,
                                listing_candidates=lambda *a: ([candidate], [], {'paginationV2': {'pageProperties': {'stores': '100', 'facet': 'fulfillment_method:Pickup'}}})), \
                 patch.object(review, 'sessions', return_value=one), patch('time.sleep'):
                result = review.run(plan, output / mode)
            assert latest.read_bytes() == b'unchanged last good'
            if mode == 'unavailable':
                assert result['completed'] and result['sessions'][0]['passed']
                row = result['sessions'][0]['accepted'][0]
                assert row['regular_price'] == row['sale_price'] == row['ppm'] == ''
            else:
                assert not result['completed'] and result['store_mismatch_seen']
                assert result['sessions'][0]['accepted'] == []
                assert result['observations'][-1]['diagnostic_only']
            checks.append('Synthetic ' + mode + ' preserves last good; invalid output rejected or unavailable retained')
    report = {'mode': 'offline synthetic checks; no retailer requests or browser launched',
              'passed': True, 'checks': checks, 'live_acceptance': False}
    atomic_json('evidence/diagnostic-20261025/step2-offline-checks.json', report)
    print(json.dumps({'passed': True, 'checks': len(checks), 'live_requests': 0}))


if __name__ == '__main__':
    check()
