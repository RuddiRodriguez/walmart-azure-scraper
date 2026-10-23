"""Offline HTTP, timeout, response-shape and canary checks; no requests are made."""
import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from bs4 import BeautifulSoup
from browser import fetch_product, navigate, canary_check
from extract import next_data


def check():
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=2, delay_seconds=0, max_page_seconds=0.02)
    store = settings['stores'][0]
    checks = []
    for status in [401, 403, 412, 429, 404, 500]:
        calls = []
        async def evaluate(*args, **kwargs):
            calls.append(1)
            return {'status': status, 'html': '<title>Response</title>'}
        loop = asyncio.new_event_loop()
        sb = SimpleNamespace(loop=loop, page=SimpleNamespace(evaluate=evaluate))
        try:
            fetch_product(sb, 'https://www.walmart.com/ip/1', settings)
        except (ValueError, RuntimeError):
            assert len(calls) == (1 if status in [401,403,412,429] else 2)
            checks.append('HTTP ' + str(status) + ' stops after expected bounded attempts')
        else:
            raise AssertionError('HTTP failure accepted')
        finally:
            loop.close()
    async def slow(*args, **kwargs):
        await asyncio.sleep(1)
    loop = asyncio.new_event_loop()
    try:
        fetch_product(SimpleNamespace(loop=loop,page=SimpleNamespace(evaluate=slow)), 'https://www.walmart.com/ip/1', settings)
    except TimeoutError:
        checks.append('Product request timeout stops collection')
    else:
        raise AssertionError('Timeout not detected')
    finally:
        loop.close()
    for html in ['<title>Ordinary page</title>', '<title>Product</title><script id="__NEXT_DATA__">not json</script>']:
        try:
            next_data(BeautifulSoup(html,'html.parser'))
        except (ValueError, TypeError, KeyError):
            checks.append('Missing or malformed retailer JSON rejected')
        else:
            raise AssertionError('Malformed JSON accepted')
    html = '<title>Offline page</title><button data-automation-id="fulfillment-banner"></button><script id="__NEXT_DATA__">{"props":{"pageProps":{"initialData":{}}}}</script>'
    sb = SimpleNamespace(goto=lambda _:None, sleep=lambda _:None, get_page_source=lambda:html)
    with patch('browser.time.monotonic', side_effect=[0,91]):
        try:
            navigate(sb,'https://www.walmart.com/cp/test/1',{**settings,'retries':1,'max_page_seconds':90},lambda *a,**k:None)
        except TimeoutError:
            checks.append('Completed navigation exceeding latency threshold rejected')
        else:
            raise AssertionError('Slow navigation accepted')
    source = json.loads(Path('evidence/source-records.json').read_text())[0]['product']
    for name, mutate in [('identity',lambda p:p.update(usItemId='999999')),
                         ('seller',lambda p:p.update(sellerName='Other')),
                         ('location',lambda p:p['location'].update(intent='SHIPPING')),
                         ('ZIP',lambda p:p['location'].update(postalCode='99999')),
                         ('pickup availability',lambda p:p.update(fulfillmentSummary=[]))]:
        product = copy.deepcopy(source); mutate(product)
        soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>','html.parser')
        soup.script.string = json.dumps({'props':{'pageProps':{'initialData':{'data':{'product':product}}}}})
        with patch('browser.fetch_product',return_value=soup):
            try:
                canary_check(None,store,settings)
            except ValueError:
                checks.append('Canary ' + name + ' change stops collection')
            else:
                raise AssertionError('Invalid canary accepted')
    result={'mode':'offline simulated HTTP/browser responses and synthetic canary mutations','passed':True,'count':len(checks),'checks':checks}
    Path('evidence/browser-failure-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    check()
