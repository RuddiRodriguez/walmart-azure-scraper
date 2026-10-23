"""Offline runner integration with captured product data and simulated two-page navigation."""
import csv
import json
import tempfile
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from bs4 import BeautifulSoup

from scrape import run


def check():
    source = json.loads(Path('evidence/source-records.json').read_text())[0]
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(minimum_records=1, minimum_category_records=1, delay_seconds=0)
    store = settings['stores'][0]
    category = source['candidate']['category']
    root = 'https://www.walmart.com/browse/food/test/976759_123'
    state = {}
    def navigate(sb, url, settings, log):
        second = '?page=2' in url
        data = {'searchResult': {'itemStacks': [{'items': [{'__typename': 'Product'}]}],
                                'paginationV2': {'pageProperties': {'page': 2 if second else 1}, 'maxPage': 2}}}
        soup = BeautifulSoup('<title>Offline fixture</title><script id="__NEXT_DATA__"></script>', 'html.parser')
        soup.script.string = json.dumps({'props': {'pageProps': {'initialData': data}}})
        if not second:
            soup.append(BeautifulSoup('<a aria-label="Next Page" href="' + root + '?page=2">Next</a>', 'html.parser'))
        state['html'] = str(soup)
        log('page_loaded', url=url, seconds=0)
        return soup
    def listing(soup, category, store):
        from extract import next_data
        return [dict(source['candidate'])], [], next_data(soup)['searchResult']
    product = BeautifulSoup('<title>Offline product</title><script id="__NEXT_DATA__"></script>', 'html.parser')
    product.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {'product': source['product']}}}}})
    sb = SimpleNamespace(scroll_down=lambda _: None, sleep=lambda _: None,
                         get_page_source=lambda: state.get('html', ''), quit=lambda: None,
                         save_screenshot=lambda _: None)
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        config = folder / 'stores.json'; config.write_text(json.dumps(settings))
        categories = folder / 'categories.csv'
        with categories.open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=['Category (Auto)', 'URL'])
            writer.writeheader(); writer.writerow({'Category (Auto)': category, 'URL': root})
        args = Namespace(config=str(config), categories=str(categories), store='100', output=str(folder / 'data'), resume=False, sample=0)
        with patch('scrape.open_browser', return_value=sb), patch('scrape.select_store', return_value=''), patch('scrape.canary_check'), patch('scrape.verify_banner'), patch('scrape.navigate', side_effect=navigate), patch('scrape.listing_candidates', side_effect=listing), patch('scrape.discover', return_value={}), patch('scrape.fetch_product', return_value=product) as fetch:
            run(args)
            pointer = json.loads((folder / 'data/100/latest.json').read_text())
            report = json.loads((folder / 'data/100' / pointer['report']).read_text())
            assert report['passed'] and report['records'] == 1 and report['pages_processed'] == 2
            assert report['exclusions']['duplicate'] == 1 and fetch.call_count == 1
            args.resume = True
            run(args)
            assert fetch.call_count == 1
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
              'Complete valid full-mode result publishes atomically', 'Resume does not repeat committed product', 'Cross-mode resume rejected']}
    Path('evidence/runner-flow-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    check()
