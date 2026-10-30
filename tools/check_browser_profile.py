"""Check optional persistent browser profile wiring without opening Chrome."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import browser


def check():
    calls = []

    with TemporaryDirectory() as folder, patch.object(
        browser.sb_cdp, 'Chrome', lambda **options: calls.append(options) or options
    ):
        with patch.dict(os.environ, {}, clear=True):
            browser.open_browser(headless=True)
        with patch.dict(os.environ, {'WALMART_BROWSER_PROFILE': folder}, clear=True):
            browser.open_browser(headless=True)

    assert calls[0]['guest'] is True
    assert 'user_data_dir' not in calls[0]
    assert calls[1]['guest'] is False
    assert calls[1]['user_data_dir'] == str(Path(folder).resolve())
    print('Browser profile wiring passed')


if __name__ == '__main__':
    check()
