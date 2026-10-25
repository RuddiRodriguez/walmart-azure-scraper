"""Bounded native pagination inspection; DOM snapshots stay private, no publication."""
import argparse
import hashlib
import json
import os
import signal
from pathlib import Path
from time import monotonic

from browser import open_browser, select_store, navigate, check_html, verify_banner
from extract import next_data
from scrape import next_page_url, verify_listing_store
from storage import atomic_json
from diagnostic_capture import safe_url


def rendered_next(sb, url, store, output, log):
    page = None
    for attempt in range(21):
        if page:
            page.decompose()
        page = check_html(sb.get_page_source())
        search = next_data(page).get('searchResult')
        verify_banner(page, store)
        verify_listing_store(search, store)
        following = next_page_url(page, url, search)
        if following or attempt == 20:
            break
        sb.scroll_down(1200)
        sb.sleep(0.4)
    try:
        body = str(page).encode()
        output.write_bytes(body)
        props = (search['paginationV2'].get('pageProperties') or {})
        result = dict(url=safe_url(url), page=int(props.get('page') or 1),
                      max_page=search['paginationV2'].get('maxPage'), store=str(props.get('stores')),
                      facet=props.get('facet'), next_url=safe_url(following) if following else None,
                      scrolls=attempt, snapshot_sha256=hashlib.sha256(body).hexdigest(),
                      snapshot_scope='Serialized rendered DOM, not original HTTP body')
        log('rendered_pagination', **result)
        return following, result
    finally:
        page.decompose()


def inspect(output):
    output = output.absolute()
    if not output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Private snapshots must stay under data/')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = settings['stores'][0]
    result = dict(completed=False, pages=[], limit_seconds=180)
    started = monotonic()
    sb = None

    def log(event, **values):
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(event=event, **values)) + '\n')

    def timeout(*_):
        raise TimeoutError('180-second pagination inspection limit')

    prior = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(180)
    try:
        sb = open_browser()
        select_store(sb, store, settings, log, output)
        url = 'https://www.walmart.com/browse/party-occasions/balloons/2637_1042319_1212898_3956207'
        for index in range(2):
            page = navigate(sb, url, settings, log)
            page.decompose()
            following, observed = rendered_next(sb, url, store, output / f'page-{index + 1}.html', log)
            result['pages'].append(observed)
            if observed['page'] != index + 1:
                raise ValueError('Observed response page does not match requested sequence')
            if index == 0 and not following:
                raise ValueError('No usable rendered next-page control')
            url = following
        result['completed'] = True
    except Exception as error:
        result['error'] = str(error)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prior)
        if sb:
            sb.quit()
        result['seconds'] = round(monotonic() - started, 3)
        atomic_json(output / 'report.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    inspect(args.output)
