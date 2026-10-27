"""Offline runner integration with captured product data and simulated two-page navigation."""
import copy
import csv
import json
import tempfile
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from bs4 import BeautifulSoup

from scrape import run, next_page_url, verify_listing_store


def check():
    source = json.loads(Path('evidence/source-records.json').read_text())[0]
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(minimum_records=1, minimum_category_records=1, delay_seconds=0)
    store = settings['stores'][0]
    category = source['candidate']['category']
    root = 'https://www.walmart.com/browse/food/test/976759_123'
    for href in ['#', '#page2', 'javascript:void(0)', '']:
        fixture = BeautifulSoup('<a aria-label="Next Page" href="' + href + '">Next</a>', 'html.parser')
        assert next_page_url(fixture, root) == ''
    fixture = BeautifulSoup('<a aria-label="Next Page" href="?page=2&amp;povid=tracking">Next</a>', 'html.parser')
    assert next_page_url(fixture, root) == root + '?page=2'
    assert next_page_url(BeautifulSoup('<a aria-label="Next Page" href="' + root + '">Next</a>', 'html.parser'), root) == root
    button = BeautifulSoup('<a aria-label="Next Page" href="#"></a>', 'html.parser')
    button.a['data-dca-extras'] = json.dumps({'custom': [{'owner': 'search', 'name': 'paginationPage', 'value': '2'}]})
    primary = {'paginationV2': {'pageProperties': {'page': 1, 'stores': '100', 'facet': 'fulfillment_method:Pickup'}, 'maxPage': 3}}
    assert next_page_url(button, root + '?facet=brand%3AExample&empty=', primary) == root + '?facet=brand%3AExample&empty=&page=2'
    verify_listing_store(primary, store)
    wrong_primary = {'paginationV2': {'pageProperties': {'page': 1, 'stores': '3081'}, 'maxPage': 3}}
    try:
        verify_listing_store(wrong_primary, store)
    except ValueError as error:
        assert 'Location mismatch' in str(error)
    else:
        raise AssertionError('Wrong-store primary listing accepted')
    button.a['data-dca-extras'] = json.dumps({'custom': [{'owner': 'search', 'name': 'paginationPage', 'value': '3'}]})
    assert next_page_url(button, root, primary) == ''
    state = {}
    def navigate(sb, url, settings, log, require_banner=True):
        second = '?page=2' in url
        data = {'searchResult': {'itemStacks': [{'items': [{'__typename': 'Product'}]}],
                                'paginationV2': {'pageProperties': {'page': 2 if second else 1, 'stores': '100', 'facet': 'fulfillment_method:Pickup'}, 'maxPage': 2}}}
        soup = BeautifulSoup('<title>Offline fixture</title><script id="__NEXT_DATA__"></script>', 'html.parser')
        soup.script.string = json.dumps({'props': {'pageProps': {'initialData': data}}})
        if not second:
            soup.append(BeautifulSoup('<a aria-label="Next Page" href="' + root + '?page=2">Next</a>', 'html.parser'))
        state['html'] = str(soup)
        state['url'] = url
        log('page_loaded', url=url, seconds=0)
        return soup
    def listing(soup, category, store):
        from extract import next_data
        return [dict(source['candidate'])], [], next_data(soup)['searchResult']
    product = BeautifulSoup('<title>Offline product</title><script id="__NEXT_DATA__"></script>', 'html.parser')
    product.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {'product': source['product']}}}}})
    sb = SimpleNamespace(scroll_down=lambda _: None, sleep=lambda _: None,
                         get_page_source=lambda: state.get('html', ''), quit=lambda: None,
                         get_current_url=lambda: state.get('url', root),
                         save_screenshot=lambda _: None)
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        config = folder / 'stores.json'; config.write_text(json.dumps(settings))
        categories = folder / 'categories.csv'
        with categories.open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=['Category (Auto)', 'URL'])
            writer.writeheader(); writer.writerow({'Category (Auto)': category, 'URL': root})
        args = Namespace(config=str(config), categories=str(categories), store='100', output=str(folder / 'data'), resume=False, sample=0)
        with patch('scrape.open_browser', return_value=sb), patch('scrape.select_store', return_value=''), patch('scrape.canary_check'), patch('scrape.verify_banner'), patch('scrape.navigate', side_effect=navigate), patch('scrape.listing_candidates', side_effect=listing), patch('scrape.discover', side_effect=lambda *a, **k: {}), patch('scrape.fetch_product', side_effect=lambda *a, **k: copy.deepcopy(product)) as fetch:
            run(args)
            pointer = json.loads((folder / 'data/100/latest.json').read_text())
            report = json.loads((folder / 'data/100' / pointer['report']).read_text())
            assert report['passed'] and report['records'] == 1 and report['pages_processed'] == 2
            assert report['exclusions']['duplicate'] == 1 and fetch.call_count == 1
            args.resume = True
            run(args)
            assert fetch.call_count == 1
            import retention
            catalog=retention.connect(folder/'data/100/catalog.sqlite', settings['stores'][0])
            retained=json.loads((folder/'data/100'/pointer['products']).read_text())[0]
            retained.update(url='https://www.walmart.com/ip/9999942',regular_price='',sale_price='',crawl_date='2020-01-01T10:00:00+00:00')
            retention.observe(catalog,'9999942',retained,'confirmed_unavailable','historical-test','2020-01-01T10:00:00+00:00',True)
            catalog.close()
            args.resume=False
            run(args)
            next_pointer=json.loads((folder/'data/100/latest.json').read_text())
            carried=json.loads((folder/'data/100'/next_pointer['products']).read_text())
            assert len(carried)==2 and next(r for r in carried if r['url'].endswith('9999942'))==retained
            next_report=json.loads((folder/'data/100'/next_pointer['report']).read_text())
            assert next_report['carried_observations']==1 and next_report['passed']
            assert fetch.call_count == 1
        original_output = args.output
        args.output = str(folder / 'location-failure'); args.resume = False
        bad_data = copy.deepcopy(source['product']); bad_data['location']['intent'] = 'SHIPPING'
        bad_product = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
        bad_product.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {'product': bad_data}}}}})
        settings['trace_store_context'] = True
        config.write_text(json.dumps(settings))
        snapshot_calls = {'count': 0}
        def snapshot(*_):
            snapshot_calls['count'] += 1
            if snapshot_calls['count'] == 4:
                raise ValueError('Synthetic unavailable context snapshot')
            return {}, None
        with patch('scrape.open_browser', return_value=sb) as opened, patch('scrape.select_store', return_value=''), patch('scrape.canary_check'), patch('scrape.verify_banner'), patch('scrape.navigate', side_effect=navigate), patch('scrape.listing_candidates', side_effect=listing), patch('scrape.discover', side_effect=lambda *a, **k: {}), patch('scrape.fetch_product', side_effect=[bad_product, copy.deepcopy(product)]) as fetch, patch('scrape.store_snapshot', side_effect=snapshot):
            run(args)
            rejected = list((folder / 'location-failure').glob('100/runs/*/sources/rejected/*.json'))
            assert len(rejected) == 1 and json.loads(rejected[0].read_text())['product']['location']['intent'] == 'SHIPPING'
            pointer = json.loads((folder / 'location-failure/100/latest.json').read_text())
            report = json.loads((folder / 'location-failure/100' / pointer['report']).read_text())
            assert report['passed'] and report['location_mismatch_seen'] and report['context_failures'] == 1
            events = [json.loads(line) for line in (folder / 'location-failure/100' / pointer['report']).parent.joinpath('events.jsonl').read_text().splitlines()]
            assert any(event['event'] == 'store_trace_unavailable' for event in events)
            assert any(event['event'] == 'product_context_retry' for event in events)
            args.resume = True
            opened.reset_mock()
            run(args)
            opened.assert_called_once()
            assert fetch.call_count == 2
        args.output = original_output
        args.sample = 2
        try:
            run(args)
        except ValueError as error:
            # Different mode uses a separate checkpoint pointer; cannot resume full output as a sample.
            assert 'No checkpoint' in str(error)
        else:
            raise AssertionError('Cross-mode resume accepted')
    result = {'mode': 'offline simulated navigation; captured product fixture; no live browser or network',
              'passed': True, 'checks': ['Two pages traversed', 'Repeated product ID deduplicated',
              'Complete valid full-mode result publishes atomically', 'Resume does not repeat committed product', 'Cross-mode resume rejected', 'Wrong location response saved and excluded', 'Freshly verified retry accepted independently', 'Context failure count retained without invalidating corrected record', 'Resume does not repeat corrected product', 'Diagnostic snapshot failure cannot hide rejected response', 'Placeholder and JavaScript next-page controls do not become URL loops', 'Real pagination URL and real loop targets preserved for validation', 'Explicit next-page metadata preserves functional filters', 'Unexpected page jumps rejected', 'Explicit wrong-store primary listing rejected', 'New full run carries unseen unavailable product without changing original date or prices']}
    result['checks'].append('Repeat run reuses cached stable details without another product request')
    Path('evidence/runner-flow-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    check()
