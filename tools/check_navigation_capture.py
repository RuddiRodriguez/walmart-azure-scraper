"""Offline checks for original browser-navigation response selection and evidence."""
import base64
import json
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup

import browser
from browser import capture_navigation, select_navigation_response
from diagnostic_capture import make_capture


def check():
    target = 'https://www.walmart.com/browse/food/976759?page=2'
    responses = [
        {'url': 'https://www.walmart.com/', 'request_id': 'home'},
        {'url': 'https://example.com/browse/food/976759', 'request_id': 'other-host'},
        {'url': 'https://www.walmart.com/browse/food/976759?page=1', 'request_id': 'first'},
        {'url': 'https://www.walmart.com/browse/food/976759?page=2', 'request_id': 'latest'},
    ]
    assert select_navigation_response(responses, target, 1)['request_id'] == 'latest'
    try:
        select_navigation_response(responses, 'https://www.walmart.com/browse/art/5899871', 0)
    except ValueError:
        pass
    else:
        raise AssertionError('Unrelated navigation response was accepted')

    document = '<title>Fixture</title><script id="__NEXT_DATA__">{}</script>'
    page = SimpleNamespace(send=lambda _: (document, False))
    sb = SimpleNamespace(
        _navigation_responses=[],
        page=page,
        loop=SimpleNamespace(run_until_complete=lambda value: value),
    )
    def navigate(*_args, **_kwargs):
        sb._navigation_responses.append({
            'url': target,
            'request_id': 'request-live-shape',
            'loader_id': 'loader-live-shape',
            'status': 200,
            'headers': {'content-type': 'text/html'},
            'protocol': 'h2',
        })
        return BeautifulSoup(document, 'html.parser')
    events = []
    with patch.object(browser, 'enable_navigation_capture'), patch.object(
            browser, 'navigate', side_effect=navigate):
        rendered, captured = capture_navigation(
            sb, target, {'max_page_seconds': 10, 'retries': 1}, lambda *_, **__: None,
            lambda event, **data: events.append((event, data)))
    assert rendered.title.string == 'Fixture' and captured.title.string == 'Fixture'
    assert [event for event, _ in events] == ['request', 'response']
    assert events[1][1]['result']['request_id'] == 'request-live-shape'

    with tempfile.TemporaryDirectory(dir='data') as folder:
        state = {'started': time.monotonic(),
                 'limits': {'product_requests': 1, 'listing_requests': 1, 'seconds': 10},
                 'product_requests': 0, 'listing_requests': 0, 'sequence': 0,
                 'body_bytes': 0}
        capture = make_capture(Path(folder), 'navigation', state, 'listing')
        capture('request', url=target, attempt=1, started_utc='synthetic', settings={})
        capture('response', result={
            'status': 200,
            'url': target,
            'redirected': False,
            'headers': {'content-type': 'text/html', 'set-cookie': 'not-saved'},
            'body_base64': base64.b64encode(b'<title>Fixture</title>').decode(),
            'request_id': 'request-123',
            'loader_id': 'loader-456',
            'resource_type': 'Document',
            'protocol': 'h2',
            'body_scope': 'Original navigation test body',
        }, received_utc='synthetic', elapsed_seconds=0)
        record = json.loads(next(Path(folder).glob('*.json')).read_text())
        assert record['response']['request_id'] == 'request-123'
        assert record['response']['loader_id'] == 'loader-456'
        assert record['response']['resource_type'] == 'Document'
        assert record['response']['protocol'] == 'h2'
        assert record['response']['headers'] == {'content-type': 'text/html'}
        assert record['body_scope'] == 'Original navigation test body'
        assert state['listing_requests'] == 1

    print(json.dumps({'passed': True, 'checks': 13, 'live_requests': 0}))


if __name__ == '__main__':
    check()
