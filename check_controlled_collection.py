"""Offline collection orchestration with synthetic transport and historical product fixture."""
import copy
import base64
import time
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup
import controlled_collection as collector


def check():
    source = json.loads(Path('evidence/source-records.json').read_text())[0]
    search = {'paginationV2': {'pageProperties': {'stores': '100', 'facet': 'fulfillment_method:Pickup', 'page': 1}, 'maxPage': 1}}
    html = '<title>Fixture</title><script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {'initialData': {'searchResult': search}}}}) + '</script>'
    checks = []
    for mode in ['success', 'wrong_store', 'empty_page', 'budget', 'product_error']:
        calls = {'product': 0}
        def fetch(sb, url, settings, capture=None):
            capture('request', url=url, attempt=1)
            if '/browse/' in url:
                return BeautifulSoup(html, 'html.parser')
            calls['product'] += 1
            if mode == 'product_error' and calls['product'] == 2:
                raise ValueError('Synthetic product parse failure')
            product = copy.deepcopy(source['product'])
            product['usItemId'] = url.split('?')[0].rsplit('/', 1)[-1]
            if mode == 'wrong_store' and calls['product'] == 2:
                product['location']['pickupLocation']['storeId'] = '3081'
            page = BeautifulSoup('<title>Fixture</title><script id="__NEXT_DATA__"></script>', 'html.parser')
            page.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {'product': product}}}}})
            return page
        def candidates(snapshot, page, category, store):
            items = []
            for key in ['5001', '5002'] if category == 'Food' else ['5002', '6001']:
                candidate = copy.deepcopy(source['candidate'])
                candidate.update(item_id=key, category=category, url='https://www.walmart.com/ip/' + key)
                items.append(candidate)
            return items, [], search
        def navigation(*_):
            if mode == 'empty_page':
                raise ValueError('Empty page title; synthetic navigation failure')
            return BeautifulSoup(html, 'html.parser')
        plan = dict(target=3, minimum_per_category=1, limits=dict(product_requests=3 if mode == 'budget' else 10, listing_requests=4, seconds=30),
                    categories=[dict(category=n, required_root='https://www.walmart.com/browse/' + path, urls=['https://www.walmart.com/browse/' + path]) for n, path in [('Food', 'food/976759'), ('Art Supplies', 'art/5899871')]])
        browser = SimpleNamespace(scroll_down=lambda _: None, sleep=lambda _: None, get_page_source=lambda: html, quit=lambda: None)
        with tempfile.TemporaryDirectory(dir='data') as folder:
            with patch.object(collector, 'open_browser', return_value=browser), patch.object(collector, 'select_store', return_value='logo'), \
                 patch.object(collector, 'verify_banner'), patch.object(collector, 'navigate', side_effect=navigation), \
                 patch.object(collector, 'fetch_product', side_effect=fetch), patch.object(collector, 'listing_from_rendered', side_effect=candidates), \
                 patch.object(collector, 'discover', return_value={}), patch.object(collector.time, 'sleep'):
                collector.run(Path(folder) / 'run', plan)
            result = json.loads((Path(folder) / 'run/report.json').read_text())
            if mode == 'success':
                assert result['target_reached'] and result['accepted_records'] == 3 and result['sample_validation']['passed']
                assert result['exclusions']['duplicate_product_id'] == 1
                checks.append('Cross-category target reached; duplicate excluded; actual schema validation passed')
            elif mode == 'wrong_store':
                assert not result['target_reached'] and result['pair_captured'] and result['accepted_records'] == 0
                checks.append('Wrong response excluded; one corrected diagnostic retry never rehabilitates run')
            elif mode == 'empty_page':
                assert not result['target_reached'] and result['completed_attempt']
                assert len(result['failures']) == 2 and result['accepted_records'] == 0
                checks.append('Both bad pages skipped once; final control reached, no retry loop')
            elif mode == 'product_error':
                assert result['completed_attempt'] and result['accepted_records'] == 2
                assert len(result['failures']) == 1
                checks.append('Ordinary product error skipped once; later products continue successfully')
            else:
                assert not result['target_reached'] and result['error'] and result['accepted_records'] == 0
                checks.append('Synthetic ' + mode + ' stops safely with partial evidence')
    for label, total, limit, allowed in [('default', 260 * 2**20, None, False),
                                          ('controlled', 260 * 2**20, 1024 * 2**20, True),
                                          ('clamped', 1024 * 2**20, 2048 * 2**20, False)]:
        with tempfile.TemporaryDirectory(dir='data') as folder:
            state = dict(started=time.monotonic(), limits=dict(product_requests=1, listing_requests=1, seconds=10),
                         product_requests=0, listing_requests=0, sequence=0, body_bytes=total)
            if limit:
                state['body_limit_bytes'] = limit
            capture = collector.make_capture(Path(folder), 'budget', state)
            capture('request', url='https://www.walmart.com/ip/1')
            try:
                capture('response', result=dict(body_base64=base64.b64encode(b'<title>Fixture</title>').decode(),
                                               status=200, url='https://www.walmart.com/ip/1'),
                        received_utc='synthetic', elapsed_seconds=0)
            except RuntimeError:
                assert not allowed
            else:
                assert allowed
            checks.append('Synthetic original-body budget ' + label + ' enforced without large allocation')
    out = Path('evidence/controlled-500-20261025');out.mkdir(exist_ok=True)
    (out/'offline-checks.json').write_text(json.dumps({'mode':'Offline synthetic transport, zero live requests','passed':True,'checks':checks},indent=2)+'\n')
    print(json.dumps({'passed':True,'checks':len(checks),'live_requests':0}))


if __name__ == '__main__':
    check()
