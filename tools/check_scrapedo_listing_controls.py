"""Offline checks for the bounded Scrape.do listing runner. No network calls."""
import io
import json
import multiprocessing
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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

    def __call__(self, token, url, deadline, byte_limit, output, clock):
        self.calls.append({'url': url, 'deadline': deadline, 'byte_limit': byte_limit})
        return self.responses.pop(0)


def response(body=None, cost='20', status=200):
    headers = {} if cost is None else {'scrape.do-request-cost': cost}
    return status, body or listing_body(), headers


def offline_token(timeout):
    assert timeout > 0
    return 'offline-test-token'


def run_case(responses=None, state=None, clock=lambda: 100.0,
             transport=None, get_token=offline_token):
    folder = tempfile.TemporaryDirectory()
    root = Path(folder.name)
    private = root / 'private'
    public = root / 'result.json'
    private.mkdir()
    if state is not None:
        (private / 'state.json').write_text(json.dumps(state))
    fetcher = transport or Fetcher(responses)
    result = runner.run(private, public, transport=fetcher, clock=clock,
                        get_token=get_token)
    report = json.loads(public.read_text())
    return folder, private, result, report, fetcher


class LateSecondFetcher(Fetcher):
    def __init__(self, now):
        super().__init__([response(), response()])
        self.now = now

    def __call__(self, token, url, deadline, byte_limit, output, clock):
        value = super().__call__(token, url, deadline, byte_limit, output, clock)
        if len(self.calls) == 2:
            self.now[0] = deadline + 100
        return value


class TrickleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', '1000')
        self.end_headers()
        try:
            for _ in range(1000):
                self.wfile.write(b'x')
                self.wfile.flush()
                time.sleep(0.02)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format_value, *args):
        pass


def shared_transport(token, url, deadline, byte_limit, output, clock):
    with (output.parent / 'calls.log').open('a') as handle:
        handle.write('request\n')
    time.sleep(0.15)
    return response()


def shared_process_run(private, public, start):
    start.wait(5)
    runner.run(Path(private), Path(public), transport=shared_transport,
               get_token=offline_token)


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
    second_state = runner.run(private, second_public, transport=second_fetcher,
                              clock=lambda: 100.0,
                              get_token=offline_token)
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

    def timed_out_token(timeout):
        raise subprocess.TimeoutExpired('security', timeout)

    folder, _, state, _, fetcher = run_case([response()], get_token=timed_out_token)
    assert not fetcher.calls and 'token acquisition exceeded' in state['stop_reason']
    checks.append('token_acquisition_is_bounded')
    folder.cleanup()

    started = time.time()
    try:
        runner.command_output(
            [sys.executable, '-c', 'import time; time.sleep(5)'],
            0.2,
        )
    except subprocess.TimeoutExpired:
        pass
    else:
        raise AssertionError('real token-style subprocess escaped timeout')
    assert time.time() - started < 2
    checks.append('real_subprocess_timeout_is_enforced')

    now = [100.0]
    late_fetcher = LateSecondFetcher(now)
    folder, _, state, report, _ = run_case(
        clock=lambda: now[0], transport=late_fetcher)
    assert not state['completed'] and state['credits_accounted'] == 40
    assert state['next_control'] == 1 and len(state['results']) == 2
    assert state['results'][1]['late_response'] is True
    assert 'after the persisted absolute deadline' in state['stop_reason']
    assert not report['completed_intended_sequence']
    checks.append('late_return_is_rejected_after_usage_accounting')
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
    uncertain['in_flight'] = {
        'attempt': 1,
        'control': 1,
        'reserved_credits': 20,
        'started_unix': 100,
    }
    folder, _, state, _, fetcher = run_case([response()], uncertain, clock=lambda: 100.0)
    assert not fetcher.calls and 'manual reconciliation' in state['stop_reason']
    checks.append('uncertain_restart_blocks_dispatch')
    folder.cleanup()

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        private = root / 'private'
        private.mkdir()
        invalid = runner.initial_state(100)
        invalid['credits_accounted'] = -1
        (private / 'state.json').write_text(json.dumps(invalid))
        fetcher = Fetcher([response()])
        try:
            runner.run(private, root / 'result.json', transport=fetcher,
                       clock=lambda: 100.0, get_token=offline_token)
        except ValueError as error:
            assert 'credits_accounted' in str(error)
        else:
            raise AssertionError('invalid resumed state was accepted')
        assert not fetcher.calls
    checks.append('invalid_resumed_state_blocks_dispatch')

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

    server = ThreadingHTTPServer(('127.0.0.1', 0), TrickleHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    with tempfile.TemporaryDirectory() as directory:
        started = time.time()
        try:
            runner.run_operation_until_deadline(
                runner.fetch_direct,
                (f'http://127.0.0.1:{server.server_port}/trickle', 2, 4096),
                started + 0.35,
                Path(directory),
            )
        except runner.DeadlineExceeded as error:
            assert error.cleanup_confirmed
        else:
            raise AssertionError('trickling body escaped the absolute deadline')
        assert time.time() - started < 2
        assert not multiprocessing.active_children()
    server.shutdown()
    server.server_close()
    checks.append('loopback_trickle_is_cancelled_and_cleaned')

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        private = root / 'private'
        context = multiprocessing.get_context('spawn')
        start = context.Event()
        first = context.Process(
            target=shared_process_run,
            args=(str(private), str(root / 'first.json'), start),
        )
        second = context.Process(
            target=shared_process_run,
            args=(str(private), str(root / 'second.json'), start),
        )
        first.start()
        second.start()
        time.sleep(0.2)
        start.set()
        first.join(10)
        second.join(10)
        assert first.exitcode == second.exitcode == 0
        calls = (private / 'calls.log').read_text().splitlines()
        saved = runner.validate_state(json.loads((private / 'state.json').read_text()))
        assert len(calls) == 2 and saved['completed']
        assert saved['attempts_dispatched'] == 2 and saved['credits_accounted'] == 40
        assert not list(private.glob('*.tmp'))
    checks.append('simultaneous_processes_share_one_allowance')

    print(json.dumps({
        'passed': True,
        'checks': checks,
        'external_network_requests': 0,
        'loopback_requests': 1,
    }, indent=2))


if __name__ == '__main__':
    check()
