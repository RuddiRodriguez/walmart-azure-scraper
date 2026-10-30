"""Offline checks for source-preserved package sizes and approximate-weight exclusions."""
import copy
import json
from pathlib import Path

from bs4 import BeautifulSoup

from extract import APPROX, package_size, product_record


def check():
    settings = json.loads(Path('config/stores.json').read_text())
    store = settings['stores'][0]
    source = json.loads(Path('evidence/source-records.json').read_text())[0]
    cases = {
        'Purina ONE Dry Dog Food 8 lb, 4 Pack': '8 lb, 4 Pack',
        'Diapers Size 4, 72 Count': '72 Count',
        '(6 Pack) Cleaning Refill 1 Gallon': '(6 Pack) 1 Gallon',
        'Snack Bags 2 x 16 oz': '2 x 16 oz',
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

    result = {
        'mode': 'Offline synthetic package-size and approximate-weight checks; no network',
        'passed': True,
        'package_size_cases': cases,
        'approximate_weight_cases': approximate,
    }
    output = Path('evidence/package-size-checks-20261030.json')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    check()
