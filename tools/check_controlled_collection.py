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
    for mode in ['success', 'wrong_store', 'wrong_identity', 'control_wrong', 'blocked', 'empty_page', 'budget', 'product_error', 'missing_price', 'unavailable']:
        calls = {'product': 0}
        def fetch(sb, url, settings, capture=None):
            capture('request', url=url, attempt=1)
            if '/browse/' in url:
                return BeautifulSoup(html, 'html.parser')
            calls['product'] += 1
            if mode == 'blocked' and calls['product'] == 2:
                raise ValueError('Access blocked: HTTP403; synthetic')
            if mode == 'product_error' and calls['product'] == 2:
                raise ValueError('Synthetic product parse failure')
            product = copy.deepcopy(source['product'])
            product['usItemId'] = url.split('?')[0].rsplit('/', 1)[-1]
            if (mode == 'wrong_store' and calls['product'] == 2) or (mode == 'control_wrong' and calls['product'] == 1):
                product['location']['pickupLocation']['storeId'] = '3081'
            if mode == 'wrong_identity' and calls['product'] == 2:
                product['usItemId'] = '999999'
            if mode == 'unavailable' and calls['product'] == 2:
                product['availabilityStatus']='OUT_OF_STOCK'
                product['fulfillmentSummary']=[]
                product['fulfillmentOptions']=[dict(type='PICKUP',locationText=json.loads(Path('config/stores.json').read_text())['stores'][0]['name'],availabilityStatus='NOT_AVAILABLE')]
                product['sellerName']=product['sellerDisplayName']=None
            page = BeautifulSoup('<title>Fixture</title><script id="__NEXT_DATA__"></script>', 'html.parser')
            page.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {'product': product}}}}})
            return page
        def candidates(snapshot, page, category, store):
            items = []
            for key in ['5001', '5002'] if category == 'Food' else ['5002', '6001']:
                candidate = copy.deepcopy(source['candidate'])
                candidate.update(item_id=key, category=category, url='https://www.walmart.com/ip/' + key)
                if mode=='missing_price' and key=='5001':
                    candidate['price_text']=''
                items.append(candidate)
            return items, [], search
        def captured_navigation(sb, url, settings, log, capture):
            capture('request', url=url, attempt=1, started_utc='synthetic',
                    settings={'transport': 'original browser navigation'})
            if mode == 'empty_page':
                capture('error', error_type='ValueError', error='Empty page title; synthetic navigation failure')
                raise ValueError('Empty page title; synthetic navigation failure')
            capture('response', result={
                'status': 200,
                'url': url,
                'redirected': False,
                'headers': {'content-type': 'text/html'},
                'body_base64': base64.b64encode(html.encode()).decode(),
                'request_id': 'request-listing',
                'loader_id': 'loader-listing',
                'resource_type': 'Document',
                'protocol': 'h2',
                'body_scope': 'Synthetic original navigation response',
            }, received_utc='synthetic', elapsed_seconds=0)
            return BeautifulSoup(html, 'html.parser'), BeautifulSoup(html, 'html.parser')
        def product_navigation(sb, url, settings, log, capture):
            return fetch(sb, url, settings, capture=capture)
        plan = dict(target=3, minimum_per_category=1, limits=dict(product_requests=3 if mode == 'budget' else 10, listing_requests=4, seconds=30),
                    categories=[dict(category=n, required_root='https://www.walmart.com/browse/' + path, urls=['https://www.walmart.com/browse/' + path]) for n, path in [('Food', 'food/976759'), ('Art Supplies', 'art/5899871')]])
        browser = SimpleNamespace(scroll_down=lambda _: None, sleep=lambda _: None, get_page_source=lambda: html, quit=lambda: None)
        with tempfile.TemporaryDirectory(dir='data') as folder:
            plan['catalog_path'] = str(Path(folder) / 'catalog.sqlite')
            with patch.object(collector, 'open_browser', return_value=browser), patch.object(collector, 'select_store', return_value='logo'), \
                 patch.object(collector, 'verify_banner'), patch.object(collector, 'capture_navigation', side_effect=captured_navigation), \
                 patch.object(collector, 'capture_product_navigation', side_effect=product_navigation), \
                 patch.object(collector, 'fetch_product', side_effect=fetch), patch.object(collector, 'listing_from_rendered', side_effect=candidates), \
                 patch.object(collector, 'discover', return_value={}), patch.object(collector.time, 'sleep'):
                collector.run(Path(folder) / 'run', plan)
            result = json.loads((Path(folder) / 'run/report.json').read_text())
            if mode in ['missing_price','unavailable']:
                assert result['target_reached'] and result['accepted_records']==3 and result['sample_validation']['passed']
                rows=json.loads((Path(folder)/'run/products.json').read_text())
                assert rows[0]['regular_price']=='' and rows[0]['sale_price']==''
                history=json.loads((Path(folder)/'run/observation-history.json').read_text())
                assert len(history)==3 and history[0]['record']['crawl_date']==rows[0]['crawl_date']
                checks.append(mode+' retained by actual collector with blank prices and durable dated history')
            elif mode == 'success':
                assert result['target_reached'] and result['accepted_records'] == 3 and result['sample_validation']['passed']
                assert result['exclusions']['duplicate_product_id'] == 1
                checks.append('Cross-category target reached; duplicate excluded; actual schema validation passed')
            elif mode == 'control_wrong':
                assert result['target_reached'] and result['accepted_records'] == 3
                assert not result['initial_control_passed'] and result['final_control_passed']
                assert result['exclusions']['control_context_rejected'] == 1
                checks.append('Bad control logged; independently valid product records still collected')
            elif mode in ['wrong_store', 'wrong_identity']:
                assert result['completed_attempt'] and result['accepted_records'] == 2
                reason = 'wrong_store_context' if mode == 'wrong_store' else 'product_identity_mismatch'
                assert result['exclusions'][reason] == 1
                assert len(result['observations']) == 3 and calls['product'] == 5
                assert not result['pair_captured']
                checks.append(mode + ' rejected without re-fetch; later products continue')
            elif mode == 'blocked':
                assert not result['completed_attempt'] and result['accepted_records'] == 0
                assert calls['product'] == 2 and 'Access blocked' in result['error']
                checks.append('Access blocking stops without further requests or bypass')
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
            plan['catalog_path'] = str(Path(folder) / 'catalog.sqlite')
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
    out = Path('evidence/retention-step2-20261026');out.mkdir(exist_ok=True)
    (out/'collector-checks.json').write_text(json.dumps({'mode':'Offline synthetic transport, zero live requests','passed':True,'checks':checks},indent=2)+'\n')
    print(json.dumps({'passed':True,'checks':len(checks),'live_requests':0}))


if __name__ == '__main__':
    check()
