"""Offline synthetic checks for root accounting and bounded discovery."""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup
import review_category_coverage as coverage


def check():
    html = '<title>Fixture</title><script id="__NEXT_DATA__">' + json.dumps(
        {'props': {'pageProps': {'initialData': {}}}}) + '</script><main>' + (
        '<a href="/browse/pets/dogs/5440_202072">Dogs</a>'
        '<a href="/browse/pets/farm-animals/5440_123">Farm Animals</a></main>')
    checks = []
    for wrong in [False, True]:
        counts = {'product': 0, 'listing': 0}

        def fetch(sb, url, settings, capture=None):
            kind = 'product' if '/ip/' in url else 'listing'
            counts[kind] += 1
            capture('request', url=url, attempt=1)
            if kind == 'listing':
                return BeautifulSoup(html, 'html.parser')
            product = {'usItemId': '47428850', 'sellerName': 'Walmart',
                       'location': {'intent': 'PICKUP', 'postalCode': '72712',
                                    'pickupLocation': {'storeId': '3081' if wrong else '100'}},
                       'fulfillmentSummary': [{'fulfillment': 'PICKUP', 'storeId': '100'}]}
            page = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
            page.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {'product': product}}}}})
            return page

        browser = SimpleNamespace(scroll_down=lambda _: None, sleep=lambda _: None,
                                  get_page_source=lambda: html, quit=lambda: None)
        with tempfile.TemporaryDirectory(dir='data') as folder:
            with patch.object(coverage, 'REVIEW', ['Pets']), \
                 patch.object(coverage, 'open_browser', return_value=browser), \
                 patch.object(coverage, 'select_store'), patch.object(coverage, 'verify_banner'), \
                 patch.object(coverage, 'navigate', side_effect=lambda *a: BeautifulSoup(html, 'html.parser')), \
                 patch.object(coverage, 'fetch_product', side_effect=fetch):
                coverage.review(Path(folder) / 'run')
            result = json.loads((Path(folder) / 'run/report.json').read_text())
            assert result['full_coverage_complete'] is False
            if wrong:
                assert not result['completed'] and not result['categories']
                assert counts == {'product': 1, 'listing': 0}
                checks.append('Wrong-store control stops before root visits; unvisited roots accounted for')
            else:
                assert result['completed'] and counts == {'product': 2, 'listing': 1}
                root = result['categories'][0]
                assert root['child_urls_not_visited'] == 1
                assert any(d['reason'] == 'brief_exclusion' for d in root['decisions'])
                assert root['native_context_verified'] is False
                checks.append('Navigation-only root retains child and excluded-link accounting without visiting children')
    out = Path('evidence/corrected-plan-20261025/step6-category-review')
    out.mkdir(exist_ok=True)
    (out/'offline-checks.json').write_text(json.dumps({'mode': 'Offline synthetic root discovery; zero live requests',
                                                     'passed': True, 'checks': checks}, indent=2) + '\n')
    print(json.dumps({'passed': True, 'checks': len(checks), 'live_requests': 0}))


if __name__ == '__main__':
    check()
