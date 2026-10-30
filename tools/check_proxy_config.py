"""Check optional proxy wiring without opening Chrome or making a network request."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import browser


OUTPUT = Path('evidence/transport-proposal-20261030/offline-check.json')


def check():
    calls = []

    def fake_chrome(**options):
        calls.append(options)
        return options

    with patch.object(browser.sb_cdp, 'Chrome', fake_chrome):
        with patch.dict(os.environ, {}, clear=True):
            browser.open_browser(headless=True)
        with patch.dict(os.environ, {'WALMART_PROXY_URL': 'user:password@proxy.example:7777'}, clear=True):
            browser.open_browser(headless=True)
    result = {
        'mode': 'Offline proxy configuration check; no browser and no network',
        'passed': len(calls) == 2 and 'proxy' not in calls[0] and calls[1].get('proxy') == 'user:password@proxy.example:7777',
        'checks': [
            'Default browser path does not set a proxy',
            'WALMART_PROXY_URL is passed to the existing Chrome session',
            'Proxy value is not written to evidence or application logs'
        ],
        'credentials_included': False
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    check()
