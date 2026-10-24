"""Review-only collection: inspect a location rejection, then preserve the original failure."""
import argparse
import hashlib
import json
from pathlib import Path

import browser
import scrape
from extract import next_data
from storage import atomic_json
from trace_store_context import product_context


def probe(sb, candidate, soup, store, settings, output):
    output.mkdir(parents=True, exist_ok=True)
    result = {'mode': 'live diagnostic after a rejected product; cannot repair or publish its run',
              'url': candidate['url'], 'observations': []}
    state, cookies = browser.store_snapshot(sb, store)
    result['before_probe'] = state
    product = next_data(soup).get('data', {}).get('product') or {}
    result['rejected_context'] = product_context(product, store)
    atomic_json(output / 'probe.json', result)
    for mode in ['same_page_fetch', 'visible_navigation']:
        page = None
        try:
            page = (browser.fetch_product(sb, candidate['url'], settings)
                    if mode == 'same_page_fetch' else browser.navigate(sb, candidate['url'], settings, lambda *a, **k: None))
            html = str(page)
            (output / (mode + '.html')).write_text(html)
            product = next_data(page).get('data', {}).get('product') or {}
            state, cookies = browser.store_snapshot(sb, store, cookies)
            result['observations'].append({'mode': mode, 'source_sha256': hashlib.sha256(html.encode()).hexdigest(),
                                           **product_context(product, store), 'visible_store': state})
        except Exception as error:
            result['observations'].append({'mode': mode, 'error': str(error)})
            break  # No continued requests after a challenge or another diagnostic failure.
        finally:
            if page is not None:
                page.clear(decompose=True)
                page.decompose()
            atomic_json(output / 'probe.json', result)


def run(args):
    original_open = scrape.open_browser
    original_parse = scrape.product_record
    sb = None
    settings = json.loads(Path(args.config).read_text())

    def open_browser(**kwargs):
        nonlocal sb
        sb = original_open(**kwargs)
        return sb

    def parse(candidate, soup, store, private_labels, logo):
        try:
            return original_parse(candidate, soup, store, private_labels, logo)
        except ValueError as error:
            if 'Location mismatch' in str(error) or 'Location ZIP mismatch' in str(error):
                try:
                    probe(sb, candidate, soup, store, {**settings, 'retries': 1, 'max_page_seconds': 25},
                          Path(args.output) / 'rejection-probe')
                except Exception as probe_error:
                    atomic_json(Path(args.output) / 'probe-failure.json', {'error': str(probe_error)})
            raise

    scrape.open_browser = open_browser
    scrape.product_record = parse
    try:
        scrape.run(args)
    finally:
        scrape.open_browser = original_open
        scrape.product_record = original_parse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/stores.json')
    parser.add_argument('--categories', default='config/categories.csv')
    parser.add_argument('--store', default='100')
    parser.add_argument('--output', required=True)
    parser.add_argument('--sample', type=int, default=3)
    parser.set_defaults(resume=False)
    run(parser.parse_args())
