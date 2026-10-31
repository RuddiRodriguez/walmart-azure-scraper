"""Recreate the client's one-valid/one-unverified full-run fixture offline."""
import copy
import csv
import json
import sqlite3
import tempfile
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup

from scrape import run


def product_page(product):
    soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
    soup.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {
        'product': product,
    }}}}})
    return soup


def check():
    source = json.loads(Path('evidence/source-records.json').read_text())[0]
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(minimum_records=1, minimum_category_records=1, delay_seconds=0)
    category = source['candidate']['category']
    root = 'https://www.walmart.com/browse/food/test/976759_123'

    valid_candidate = copy.deepcopy(source['candidate'])
    valid_product = copy.deepcopy(source['product'])
    unverified_candidate = copy.deepcopy(valid_candidate)
    unverified_candidate['item_id'] = '47428851'
    unverified_candidate['url'] = 'https://www.walmart.com/ip/Unverified-Fixture/47428851'
    unverified_candidate['item']['usItemId'] = '47428851'
    unverified_candidate['item']['name'] = 'Unverified assortment fixture'
    unverified_candidate['item']['fulfillmentSummary'] = []

    unverified_product = copy.deepcopy(valid_product)
    unverified_product['usItemId'] = '47428851'
    unverified_product['name'] = 'Unverified assortment fixture'
    unverified_product['fulfillmentSummary'] = []
    unverified_product['fulfillmentOptions'] = []
    corrected_product = copy.deepcopy(unverified_product)
    corrected_product['fulfillmentSummary'] = copy.deepcopy(valid_product['fulfillmentSummary'])

    search = {'searchResult': {
        'itemStacks': [{'items': [valid_candidate['item'], unverified_candidate['item']]}],
        'paginationV2': {'pageProperties': {
            'page': 1, 'stores': '100', 'facet': 'fulfillment_method:Pickup',
        }, 'maxPage': 1},
    }}
    listing_page = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
    listing_page.script.string = json.dumps({'props': {'pageProps': {'initialData': search}}})
    state = {'html': str(listing_page), 'url': root}
    browser = SimpleNamespace(
        scroll_down=lambda _: None,
        sleep=lambda _: None,
        get_page_source=lambda: state['html'],
        get_current_url=lambda: state['url'],
        save_screenshot=lambda _: None,
        quit=lambda: None,
    )

    def navigate(_browser, url, _settings, log, require_banner=True):
        state['url'] = url
        log('page_loaded', url=url, seconds=0)
        return copy.deepcopy(listing_page)

    def listing(_soup, _category, _store):
        return [copy.deepcopy(valid_candidate), copy.deepcopy(unverified_candidate)], [], search['searchResult']

    with tempfile.TemporaryDirectory(dir='data') as folder:
        folder = Path(folder)
        config = folder / 'stores.json'
        config.write_text(json.dumps(settings))
        categories = folder / 'categories.csv'
        with categories.open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=['Category (Auto)', 'URL'])
            writer.writeheader()
            writer.writerow({'Category (Auto)': category, 'URL': root})
        args = Namespace(
            config=str(config), categories=str(categories), store='100',
            output=str(folder / 'data'), resume=False, sample=0,
        )
        common = [
            patch('scrape.open_browser', return_value=browser),
            patch('scrape.select_store', return_value=''),
            patch('scrape.canary_check'),
            patch('scrape.verify_banner'),
            patch('scrape.navigate', side_effect=navigate),
            patch('scrape.listing_candidates', side_effect=listing),
            patch('scrape.discover', return_value={}),
        ]
        with common[0], common[1], common[2], common[3], common[4], common[5], common[6], \
                patch('scrape.fetch_product', side_effect=[
                    product_page(valid_product), product_page(unverified_product),
                ]) as first_fetch:
            try:
                run(args)
            except RuntimeError as error:
                assert 'Full run failed publication checks' in str(error)
            else:
                raise AssertionError('Unverified assortment fixture published')
        base = folder / 'data/100'
        run_folder = next((base / 'runs').iterdir())
        report = json.loads((run_folder / 'report.json').read_text())
        failure = json.loads((run_folder / 'failure.json').read_text())
        review = json.loads((run_folder / 'assortment-review.json').read_text())
        checkpoint = sqlite3.connect(run_folder / 'checkpoint.sqlite')
        states = dict(checkpoint.execute('SELECT id,status FROM candidates'))
        reasons = dict(checkpoint.execute('SELECT id,reason FROM candidates'))
        checkpoint.close()
        assert first_fetch.call_count == 2
        assert not report['passed'] and report['pending_products'] == 1
        assert failure['pending_products'] == 1 and failure['published'] is False
        assert states == {'47428850': 'done', '47428851': 'pending'}
        assert reasons['47428851'] == 'retained_assortment_unverified'
        assert len(review) == 1 and review[0]['url'].endswith('/47428851')
        assert not (base / 'latest.json').exists()

        args.resume = True
        with patch('scrape.open_browser', return_value=browser), \
                patch('scrape.select_store', return_value=''), \
                patch('scrape.canary_check'), patch('scrape.verify_banner'), \
                patch('scrape.navigate', side_effect=navigate), \
                patch('scrape.listing_candidates', side_effect=listing), \
                patch('scrape.discover', return_value={}), \
                patch('scrape.fetch_product', return_value=product_page(corrected_product)) as resume_fetch:
            run(args)
        pointer = json.loads((base / 'latest.json').read_text())
        resumed = json.loads((base / pointer['report']).read_text())
        assert resume_fetch.call_count == 1
        assert resumed['passed'] and resumed['pending_products'] == 0
        assert resumed['records'] == 2

    result = {
        'mode': 'Offline client fixture; no browser, network, or live publication',
        'passed': True,
        'first_run': {
            'valid_products': 1,
            'unverified_products': 1,
            'pending_products': 1,
            'published': False,
        },
        'resume': {
            'unverified_candidate_retried': True,
            'published_only_after_eligibility_proof': True,
            'records': 2,
        },
    }
    output = Path('evidence/unverified-assortment-gate-20261031.json')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    check()
