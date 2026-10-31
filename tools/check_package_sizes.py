"""Offline checks for source-preserved package sizes and approximate-weight exclusions."""
import copy
import json
from pathlib import Path

from bs4 import BeautifulSoup

from extract import APPROX, FIELDS, package_size, product_record
from validate import validate


def check():
    settings = json.loads(Path('config/stores.json').read_text())
    store = settings['stores'][0]
    source = json.loads(Path('evidence/source-records.json').read_text())[0]
    cases = {
        'Purina ONE Dry Dog Food 8 lb, 4 Pack': '8 lb, 4 Pack',
        'Diapers Size 4, 72 Count': '72 Count',
        '(6 Pack) Cleaning Refill 1 Gallon': '(6 Pack) 1 Gallon',
        'Snack Bags 2 x 16 oz': '2 x 16 oz',
        'Soup 12 oz (Pack of 4)': '12 oz (Pack of 4)',
        'Cleaner Pack of 6, 1 Gallon': 'Pack of 6, 1 Gallon',
        'Chocolate 250 g': '250 g',
        'Juice 1 L': '1 L',
        'Water 12 oz, 6 Bottles': '12 oz, 6 Bottles',
    }
    for title, expected in cases.items():
        assert package_size(title) == expected, title

    approximate = [
        'Average Weight 1 lb', 'Avg. Wt 2 lb', 'Approximately 3 lb',
        'About 4 lb', 'Variable Weight', 'Weight May Vary',
    ]
    for title in approximate:
        assert APPROX.search(title), title

    product = copy.deepcopy(source['product'])
    product['name'] = 'Purina ONE Dry Dog Food 8 lb, 4 Pack'
    soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
    payload = {'props': {'pageProps': {'initialData': {'data': {
        'product': product, 'idml': {'specifications': []}}}}}}
    soup.script.string = json.dumps(payload)
    row, reason, _ = product_record(
        source['candidate'], soup, store, settings['private_labels'], '')
    assert row['weight'] == '8 lb, 4 Pack' and reason == ''

    product = copy.deepcopy(source['product'])
    product['name'] = 'Fresh Product'
    soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
    payload = {'props': {'pageProps': {'initialData': {'data': {
        'product': product, 'idml': {
            'specifications': [{'name': 'Weight', 'value': 'Average Weight 1 lb'}]}}}}}}
    soup.script.string = json.dumps(payload)
    row, reason, _ = product_record(
        source['candidate'], soup, store, settings['private_labels'], '')
    assert row is None and reason == 'approximate_weight'

    historical = dict.fromkeys(FIELDS, '')
    historical.update(
        zipcode=store['zip'], store_name=store['name'], store_location=store['address'],
        category='Food', product_title='Average Weight 1 lb', weight='1 lb',
        regular_price='1.00', image_url='https://example.com/product.jpg',
        url='https://www.walmart.com/ip/Historical-Product/123456',
        crawl_date='2026-10-01T12:00:00+00:00')
    checked = validate(
        [historical], ['Food'], store,
        {**settings, 'minimum_records': 1, 'minimum_category_records': 1}, 0, 0, 0)
    assert not checked['passed']
    assert 'Record 0: forbidden field value' in checked['errors']

    product = copy.deepcopy(source['product'])
    product['name'] = 'Fresh Product Average Weight 1 lb'
    soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
    payload = {'props': {'pageProps': {'initialData': {'data': {
        'product': product, 'idml': {'specifications': []}}}}}}
    soup.script.string = json.dumps(payload)
    row, reason, _ = product_record(
        source['candidate'], soup, store, settings['private_labels'], '')
    assert row is None and reason == 'approximate_weight'

    result = {
        'mode': 'Offline synthetic package-size and approximate-weight checks; no network',
        'passed': True,
        'package_size_cases': cases,
        'approximate_weight_cases': approximate,
        'historical_title_filter': 'Average Weight 1 lb blocks publication',
    }
    output = Path('evidence/package-size-checks-20261030.json')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    check()
