"""Focused offline listing-gate and crawler integration checks; no live requests."""
import json
import tempfile
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock

from bs4 import BeautifulSoup
from scrape import verify_listing_store, run


def check():
    store = {'id': '100'}
    cases = [
        ('correct', {'stores': '100', 'facet': 'fulfillment_method:Pickup'}, True),
        ('wrong_store', {'stores': '3081', 'facet': 'fulfillment_method:Pickup'}, False),
        ('missing_store', {'facet': 'fulfillment_method:Pickup'}, False),
        ('missing_pickup', {'stores': '100'}, False),
        ('shipping', {'stores': '100', 'facet': 'fulfillment_method:Shipping'}, False),
        ('conflicting_intents', {'stores': '100', 'facet': 'fulfillment_method:Pickup||fulfillment_method:Shipping'}, False),
        ('pickup_prefix_is_not_pickup', {'stores': '100', 'facet': 'fulfillment_method:PickupToday'}, False),
        ('other_facets', {'stores': 100, 'facet': 'brand:Clorox||fulfillment_method:Pickup'}, True),
    ]
    results = []
    for name, props, expected in cases:
        try:
            accepted = verify_listing_store({'paginationV2': {'pageProperties': props}}, store)
        except ValueError:
            accepted = False
        assert accepted == expected, name
        results.append(name)
    assert verify_listing_store(None, store, require_context=False) is False
    results.append('navigation_without_context_not_price_verified')

    for navigation in [False, True]:
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder) / '100'
            base.mkdir()
            prior = b'{"run_id":"last-good"}\n'
            (base / 'latest.json').write_bytes(prior)
            args = Namespace(config='config/stores.json', categories='config/categories.csv',
                             store='100', output=folder, resume=False, sample=0)
            browser = SimpleNamespace(scroll_down=Mock(), sleep=Mock(),
                                      get_page_source=lambda: '<html></html>', quit=Mock())
            candidate = {'item_id': '123'}
            with patch('scrape.open_browser', return_value=browser), \
                 patch('scrape.select_store', return_value=''), \
                 patch('scrape.canary_check'), patch('scrape.verify_banner'), \
                 patch('scrape.navigate', side_effect=lambda *a: BeautifulSoup('<html></html>', 'html.parser')), \
                 patch('scrape.listing_candidates', return_value=([] if navigation else [candidate], [], None)), \
                 patch('scrape.fetch_product') as fetch, \
                 patch('scrape.discover', return_value={'https://www.walmart.com/browse/child/1': 'Child'}) as discovery, \
                 patch('scrape.save_page', side_effect=RuntimeError('offline stop after discovery')) as save:
                try:
                    run(args)
                except (ValueError, RuntimeError) as error:
                    if navigation:
                        assert str(error) == 'offline stop after discovery'
                        discovery.assert_called_once()
                        assert 'https://www.walmart.com/browse/child/1' in save.call_args.args[3]
                    else:
                        assert 'context missing' in str(error)
                        discovery.assert_not_called()
                        save.assert_not_called()
                else:
                    raise AssertionError('Offline run did not stop')
                fetch.assert_not_called()
            assert (base / 'latest.json').read_bytes() == prior
            failure = json.loads(next((base / 'runs').glob('*/failure.json')).read_text())
            assert failure['published'] is False
            assert failure['location_mismatch_seen'] is (not navigation)
            results.append('navigation_children_preserved' if navigation else 'unverified_candidates_never_queued_or_fetched')
    output = Path('evidence/corrected-plan-20261025/step3-review/listing-check-tests.json')
    output.write_text(json.dumps({'mode': 'Offline synthetic unit and crawler integration checks; zero live requests',
                                  'passed': True, 'checks': results}, indent=2) + '\n')
    print(json.dumps({'passed': True, 'checks': len(results), 'live_requests': 0}))


if __name__ == '__main__':
    check()
