"""Offline checks for the bounded Scrape.do listing runner. No network calls."""
import io
import json
import tempfile
from pathlib import Path

from tools import run_scrapedo_listing_controls as runner


def listing_body(store='100', zip_code='72712', availability='IN_STOCK', linked=True):
    item = {
        '__typename': 'Product',
        'usItemId': '10450114',
        'priceInfo': {'currentPrice': {'price': 2.88, 'currencyUnit': 'USD'}},
        'fulfillmentOptions': [{
            'type': 'PICKUP',
            'selected': True,
            'intent': True,
            'availabilityStatus': availability,
        }],
        'availableFulfillmentOptions': ['PICKUP'] if linked else [],
        'fulfillmentSummary': [],
    }
    data = {
        'props': {'pageProps': {'initialData': {'data': {
            'contentLayout': {'pageMetadata': {'location': {
                'storeId': store,
                'pickupStore': store,
                'postalCode': zip_code,
                'intent': 'PICKUP',
            }}},
            'searchResult': {
                'catInfo': {'catId': runner.EXPECTED_CATEGORY_ID},
                'paginationV2': {'pageProperties': {
                    'cat_id': runner.EXPECTED_CATEGORY_ID,
                    'stores': store,
                    'facet': 'fulfillment_method:Pickup',
                }},
                'itemStacks': [{'items': [item]}],
            },
        }}}},
    }
    return ('<html><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(data) + '</script></html>').encode()


class Fetcher:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, token, url, timeout, byte_limit):
        self.calls.append({'url': url, 'timeout': timeout, 'byte_limit': byte_limit})
        return self.responses.pop(0)


def response(body=None, cost='20', status=200):
    headers = {} if cost is None else {'scrape.do-request-cost': cost}
    return status, body or listing_body(), headers


def run_case(responses, state=None, clock=lambda: 100.0):
    folder = tempfile.TemporaryDirectory()
    root = Path(folder.name)
    private = root / 'private'
    public = root / 'result.json'
    private.mkdir()
    if state is not None:
        (private / 'state.json').write_text(json.dumps(state))
    fetcher = Fetcher(responses)
    result = runner.run(private, public, fetcher=fetcher, clock=clock,
                        get_token=lambda: 'offline-test-token')
    report = json.loads(public.read_text())
    return folder, private, result, report, fetcher


def check():
    checks = []

    folder, _, state, report, fetcher = run_case([response(), response()])
    assert state['completed'] and report['completed_intended_sequence']
    assert len(fetcher.calls) == 2 and state['credits_accounted'] == 40
    checks.append('complete_sequence_required')
    folder.cleanup()

    folder, private, state, _, fetcher = run_case([response(body=listing_body(store='3081')), response()])
    assert not state['completed'] and len(fetcher.calls) == 1
    assert 'rejected' in state['stop_reason']
    checks.append('wrong_store_stops_immediately')
    second_fetcher = Fetcher([response()])
    second_public = private.parent / 'second-result.json'
    second_state = runner.run(private, second_public, fetcher=second_fetcher,
                              clock=lambda: 100.0,
                              get_token=lambda: 'offline-test-token')
    assert not second_fetcher.calls and second_state['stop_reason']
    checks.append('terminal_stop_survives_restart')
    folder.cleanup()

    folder, _, state, _, fetcher = run_case([response(cost='21'), response()])
    assert not state['completed'] and len(fetcher.calls) == 1
    assert 'usage exceeded' in state['stop_reason']
    checks.append('unexpected_usage_stops_immediately')
    folder.cleanup()

    timed_state = runner.initial_state(0)
    folder, _, state, _, fetcher = run_case([response()], timed_state, clock=lambda: 299.0)
    assert not state['completed'] and not fetcher.calls
    assert 'absolute deadline' in state['stop_reason']
    checks.append('absolute_deadline_checked_before_dispatch')
    folder.cleanup()

    folder, private, state, _, fetcher = run_case([response(cost=None), response()])
    assert not state['completed'] and len(fetcher.calls) == 1 and state['in_flight']
    assert state['credits_accounted'] == 0 and 'usage is uncertain' in state['stop_reason']
    persisted = json.loads((private / 'state.json').read_text())
    assert persisted['in_flight']
    checks.append('missing_usage_is_uncertain_and_persisted')
    folder.cleanup()

    folder, private, state, _, fetcher = run_case([response(cost='unknown')])
    assert state['in_flight'] and 'not an integer' in state['stop_reason']
    checks.append('invalid_usage_is_not_zero')
    folder.cleanup()

    resumed = runner.initial_state(0)
    resumed.update({
        'attempts_dispatched': 2,
        'credits_accounted': 40,
        'next_control': 1,
    })
    folder, _, state, _, fetcher = run_case([response()], resumed, clock=lambda: 100.0)
    assert state['completed'] and state['attempts_dispatched'] == 3
    assert state['credits_accounted'] == 60 and len(fetcher.calls) == 1
    checks.append('cumulative_counters_survive_restart')
    folder.cleanup()

    uncertain = runner.initial_state(0)
    uncertain['attempts_dispatched'] = 1
    uncertain['in_flight'] = {'attempt': 1, 'control': 1, 'reserved_credits': 20}
    folder, _, state, _, fetcher = run_case([response()], uncertain, clock=lambda: 100.0)
    assert not fetcher.calls and 'manual reconciliation' in state['stop_reason']
    checks.append('uncertain_restart_blocks_dispatch')
    folder.cleanup()

    partial = [response(), response(status=500)]
    folder, _, state, report, fetcher = run_case(partial)
    assert not state['completed'] and state['next_control'] == 1
    assert not report['completed_intended_sequence'] and len(fetcher.calls) == 2
    checks.append('partial_sequence_cannot_pass')
    folder.cleanup()

    parsed = runner.parse_listing(listing_body(availability=None), runner.LISTING_URL)
    assert not runner.accepted(parsed)
    checks.append('pickup_availability_required')

    parsed = runner.parse_listing(listing_body(linked=False), runner.LISTING_URL)
    assert not runner.accepted(parsed)
    checks.append('price_and_pickup_source_link_required')

    try:
        runner.read_bounded(io.BytesIO(b'x' * 11), 10)
    except runner.ResponseTooLarge:
        pass
    else:
        raise AssertionError('oversized response was accepted')
    checks.append('response_read_is_bounded')

    redirect = runner.NoRedirectHandler().redirect_request(None, None, 302, '', {}, 'https://example.com')
    assert redirect is None
    checks.append('redirects_disabled')

    print(json.dumps({'passed': True, 'checks': checks, 'network_requests': 0}, indent=2))


if __name__ == '__main__':
    check()
