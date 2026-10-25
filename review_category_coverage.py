"""Bounded root-page coverage review; discovers links but never crawls or publishes them."""
import argparse
import csv
from collections import Counter
import hashlib
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from browser import open_browser, select_store, navigate, verify_banner, fetch_product
from diagnostic_capture import make_capture, safe_url
from extract import discover, listing_candidates, next_data, pickup, category_id
from scrape import verify_listing_store
from storage import atomic_json, page_url
from trace_store_context import product_context


REVIEW = ['Personal Care', 'Beauty', 'Feeding', 'Health & Wellness', 'Pets', 'Art Supplies', 'Office Supplies']


def review(output, plan=None):
    output = Path(output).absolute()
    if not output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Private evidence must stay under data/')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = settings['stores'][0]
    roots = list(csv.DictReader(Path('config/categories.csv').open()))
    cases = json.loads(Path(plan).read_text()) if plan else [dict(category=n, url=next(r['URL'] for r in roots if r['Category (Auto)'] == n)) for n in REVIEW]
    if not 0 < len(cases) <= 7 or len({c['category'] for c in cases}) != len(cases):
        raise ValueError('Coverage review requires one to seven distinct categories')
    for case in cases:
        required = next(r for r in roots if r['Category (Auto)'] == case['category'])
        if plan and (not case['url'].startswith('https://www.walmart.com/browse/') or category_id(required['URL']) not in category_id(case['url']).split('_')):
            raise ValueError('Selected child must have explicit required-root ancestry')
    state = dict(started=time.monotonic(), limits=dict(product_requests=2, listing_requests=7, seconds=600),
                 product_requests=0, listing_requests=0, sequence=0, body_bytes=0)
    result = dict(mode='Live bounded category-root discovery only; no child crawl or publication',
                  started_utc=datetime.now(timezone.utc).isoformat(), completed=False, categories=[],
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  source_hashes={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
                                 ['review_category_coverage.py', 'scrape.py', 'extract.py', 'browser.py', 'config/categories.csv']},
                  limits=state['limits'], selected_plan=cases)
    sb = None

    def log(event, **values):
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(event=event, **values)) + '\n')

    def save():
        result['counts'] = {k: state[k] for k in ['product_requests', 'listing_requests', 'sequence', 'body_bytes']}
        result['seconds'] = round(time.monotonic() - state['started'], 3)
        atomic_json(output / 'report.json', result)

    def control():
        url = store['canary_urls'][0]
        page = fetch_product(sb, url, settings, capture=make_capture(output / 'captures', 'coverage', state))
        try:
            product = next_data(page).get('data', {}).get('product') or {}
            if (not product_context(product, store)['store_matches'] or not pickup(product, store)
                    or str(product.get('usItemId')) != url.split('?')[0].rsplit('/', 1)[-1]
                    or (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart', 'Walmart.com']):
                raise ValueError('Coverage control store/identity/pickup/seller mismatch')
        finally:
            page.decompose()

    def timeout(*_):
        raise TimeoutError('Category review ten-minute limit')

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    save()
    try:
        sb = open_browser()
        select_store(sb, store, settings, log, output)
        control()
        for case in cases:
            name = case['category']
            root = next(r for r in roots if r['Category (Auto)'] == name)
            url = page_url(case['url'])
            entry = dict(category=name, url=safe_url(url), status='started', decisions=[])
            result['categories'].append(entry)
            save()
            native = navigate(sb, url, settings, log)
            try:
                verify_banner(native, store)
                # Match production's bounded lazy-card settling without fetching child pages.
                stable, prior = 0, -1
                for _ in range(20):
                    sb.scroll_down(900)
                    sb.sleep(0.4)
                    native.decompose()
                    native = BeautifulSoup(sb.get_page_source(), 'html.parser')
                    verify_banner(native, store)
                    count = len(native.select('[data-item-id]'))
                    stable = stable + 1 if count == prior else 0
                    prior = count
                    if stable >= 4:
                        break
                else:
                    raise ValueError('Root lazy loading did not settle within20scrolls')
                body = str(native).encode()
                (output / f'root-{len(result["categories"])}.html').write_bytes(body)
                entry['native_snapshot_sha256'] = hashlib.sha256(body).hexdigest()
                candidates, rejected, search = listing_candidates(native, name, store)
                entry['native_context_verified'] = verify_listing_store(search, store, require_context=bool(candidates))
                entry['rejected_candidate_reasons'] = dict(Counter(c['reason'] for c in rejected))
                links = discover(native, page_url(root['URL']), ['recipes', r'shop[- ]all[- ]foods?$', 'farm[- ]animals'],
                                 current_url=url, decisions=entry['decisions'])
                entry.update(visible_candidates=len(candidates), excluded_candidates=len(rejected),
                             discovered_child_urls=list(links), child_urls_not_visited=len(links))
            finally:
                native.decompose()
            fetched = fetch_product(sb, url, settings,
                                    capture=make_capture(output / 'captures', 'coverage', state, 'listing'))
            try:
                search = next_data(fetched).get('searchResult')
                props = ((search or {}).get('paginationV2') or {}).get('pageProperties') or {}
                entry['fetch_context_verified'] = verify_listing_store(search, store, require_context=False)
                entry['fetch_context'] = {k: props.get(k) for k in ['stores', 'facet', 'page']}
                entry['fetch_sequence'] = state['sequence']
                entry['status'] = 'root_reviewed_children_not_crawled'
            finally:
                fetched.decompose()
            save()
        control()
        result['completed'] = True
    except Exception as error:
        result.update(error=str(error), error_type=type(error).__name__)
        if result['categories'] and result['categories'][-1]['status'] == 'started':
            result['categories'][-1].update(status='failed', error=str(error))
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
        if sb:
            sb.quit()
        attempted = {r['category'] for r in result['categories']}
        result['not_visited'] = [dict(category=n, reason='bounded run stopped before visit') for n in [c['category'] for c in cases] if n not in attempted]
        result['full_coverage_complete'] = False
        save()
    print(json.dumps({k: result.get(k) for k in ['completed', 'counts', 'seconds', 'error']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    review(args.output, args.plan)
