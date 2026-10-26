"""Offline orchestration checks; all retailer responses below are synthetic."""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
import capture_store_drift as review


def check():
    results = []
    for mode in ['normal', 'drift', 'pagination_gap', 'rendered_fallback', 'extended', 'artsets']:
        drift = mode == 'drift'
        gap = mode in ['pagination_gap', 'rendered_fallback']
        counts = {'listings': 0, 'products': 0}

        def page():
            return BeautifulSoup('<html></html>', 'html.parser')

        def fetch(sb, url, settings, capture=None):
            capture('request', url=url, attempt=1)
            if '/browse/' in url:
                counts['listings'] += 1
            else:
                counts['products'] += 1
                counts['id'] = url.rsplit('/', 1)[-1]
            return page()

        def candidates(*_):
            start = counts['listings'] * 100
            return ([{'item_id': str(i), 'url': f'https://www.walmart.com/ip/{i}'}
                     for i in range(start, start + 10)], [], {'paginationV2': {'maxPage': 2, 'pageProperties': {'page': 1}}})

        def context(*_):
            return {'product_id': 'synthetic', 'store_matches': not drift or counts['products'] > 1}

        Path('data').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir='data') as folder:
            with patch.object(review, 'open_browser', return_value=Mock()), \
                 patch.object(review, 'select_store', return_value=''), \
                 patch.object(review, 'store_snapshot', return_value=({}, {})), \
                 patch.object(review, 'navigate', side_effect=lambda *a: page()), \
                 patch.object(review, 'verify_banner'), patch.object(review, 'verify_listing_store'), \
                 patch.object(review, 'next_page_url', side_effect=lambda p, url, search: None if gap else url + '?page=next'), \
                 patch.object(review, 'rendered_next', return_value=('https://www.walmart.com/browse/test?page=2', {'page': 1})), \
                 patch.object(review, 'fetch_product', side_effect=fetch), \
                 patch.object(review, 'listing_candidates', side_effect=candidates), \
                 patch.object(review, 'next_data', return_value={'data': {'product': {'usItemId': 'synthetic'}}}), \
                 patch.object(review, 'product_context', side_effect=context), \
                 patch.object(review, 'product_record', return_value=({'synthetic': True}, '', {})), \
                 patch.object(review.time, 'sleep'):
                def data(*_):
                    return {'data': {'product': {'usItemId': counts['id']}}}
                with patch.object(review, 'next_data', side_effect=data):
                    result = review.run(Path(folder) / 'run', pages=3, rendered=mode == 'rendered_fallback', extended=mode == 'extended', artsets=mode == 'artsets')
            if drift:
                assert not result['completed'] and result['pair_captured']
                assert result['counts']['product_requests'] == 2
                assert result['accepted'] == []
                results.append('Synthetic wrong/correct pair stops invalid run; retry cannot publish')
            elif mode == 'pagination_gap':
                assert result['attempt_finished'] and not result['completed']
                assert len(result['pagination_gaps']) == 2
                assert result['counts']['listing_requests'] == 4
                results.append('Reported extra pages without next controls leave expanded scope incomplete')
            elif mode == 'artsets':
                assert result['completed'] and len(result['accepted']) == 5
                assert result['counts']['product_requests'] == 5 and result['counts']['listing_requests'] == 1
                assert result['limits'] == {'product_requests': 6, 'listing_requests': 1, 'seconds': 180}
                results.append('ArtSets profile bounded to5targets/onepage/180seconds plus one diagnostic re-fetch')
            elif mode == 'extended':
                assert result['completed'] and len(result['accepted']) == 70
                assert result['counts']['product_requests'] == 70
                assert result['counts']['listing_requests'] == 9
                assert result['limits']['product_requests'] == 72
                assert result['limits']['listing_requests'] == 20
                results.append('Extended synthetic scope reaches70targets within72product/20listing bounds')
            else:
                assert result['completed']
                assert result['counts']['listing_requests'] == 8
                assert result['counts']['product_requests'] == 57
                assert len(result['accepted']) == 57
                results.append('Synthetic paginated orchestration respects request limits')
    path = Path('evidence/corrected-plan-20261025/art-product-test/offline-checks.json')
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({'mode': 'Offline synthetic orchestration only; not real drift evidence',
                               'passed': True, 'checks': results}, indent=2) + '\n')
    print(json.dumps({'passed': True, 'checks': len(results), 'live_requests': 0}))


if __name__ == '__main__':
    check()
