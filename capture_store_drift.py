"""One bounded same-session drift investigation; private evidence, no publication."""
import argparse
import hashlib
import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from browser import open_browser, select_store, navigate, verify_banner, fetch_product, store_snapshot
from diagnostic_capture import make_capture, safe_url
from extract import listing_candidates, next_data, product_record
from scrape import next_page_url, verify_listing_store
from inspect_rendered_pagination import rendered_next
from storage import atomic_json
from trace_store_context import product_context


CATEGORIES = [
    ('Balloons', 'party-occasions/balloons/2637_1042319_1212898_3956207', 24),
    ('Diapering', 'diapering/5427_486190', 24),
    ('Food', 'food/porch-pumpkins/976759_976793_8739812', 5),
    ('Household Essentials', 'household-essentials/clorox/1115193_8250903_7784444', 4),
]


def listing_from_rendered(snapshot, fetched, category, store):
    """Match visible native cards against the separately captured listing response."""
    native = BeautifulSoup(Path(snapshot).read_bytes(), 'html.parser')
    try:
        primary = next_data(native).get('searchResult')
        captured = next_data(fetched).get('searchResult')
        verify_listing_store(primary, store)
        verify_listing_store(captured, store)
        native_page = (primary['paginationV2'].get('pageProperties') or {}).get('page', 1)
        fetched_page = (captured['paginationV2'].get('pageProperties') or {}).get('page', 1)
        if str(native_page) != str(fetched_page):
            raise ValueError('Rendered and captured listing page identifiers differ')
        # Existing extractor now uses raw-response item IDs/flags with visible cards.
        native.select_one('#__NEXT_DATA__').string = fetched.select_one('#__NEXT_DATA__').string
        return listing_candidates(native, category, store)
    finally:
        native.decompose()


def run(output, pages=1, rendered=False, extended=False, rendered_cards=False, artsets=False):
    if artsets and extended:
        raise ValueError("Select one bounded profile")
    if rendered_cards and not rendered:
        raise ValueError("Rendered candidates require rendered pagination snapshots")
    if pages not in [1, 3]:
        raise ValueError("Use one or three pages per large category")
    output = output.absolute()
    if not output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Evidence must stay under ignored data/')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = settings['stores'][0]
    cases = [(category, path, quota) for (category, path, _), quota in zip(CATEGORIES, [27, 32, 5, 6])] if extended else CATEGORIES
    page_limits = dict(zip([c[0] for c in CATEGORIES], [5, 11, 1, 3])) if extended else {}
    limits = dict(product_requests=72 if extended else 60, listing_requests=20 if extended else 2 * pages + 2, seconds=1200)
    if artsets:
        cases = [('Art Supplies', 'arts-crafts-sewing/art-sets/1334134_5899871_7148292', 5)]
        page_limits = {'Art Supplies': 1}
        limits = dict(product_requests=6, listing_requests=1, seconds=180)
    state = dict(started=time.monotonic(), limits=limits,
                 product_requests=0, listing_requests=0, sequence=0, body_bytes=0)
    report = dict(started_utc=datetime.now(timezone.utc).isoformat(), completed=False,
                  pair_captured=False, listings=[], rendered_candidates=rendered_cards, pagination_gaps=[], observations=[], accepted=[], category_visits=0,
                  pages_per_large_category=pages, rendered_pagination=rendered, extended=extended, artsets=artsets, target_product_ceiling=sum(c[2] for c in cases), limits=state['limits'], mode='Private live diagnostic; no production output',
                  source_hashes={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                 for p in ['capture_store_drift.py', 'browser.py', 'extract.py', 'diagnostic_capture.py', 'scrape.py', 'inspect_rendered_pagination.py']})
    sb = None

    def save():
        report['counts'] = {k: state[k] for k in ['product_requests', 'listing_requests', 'sequence', 'body_bytes']}
        report['seconds'] = round(time.monotonic() - state['started'], 3)
        atomic_json(output / 'report.json', report)

    def log(event, **values):
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(time_utc=datetime.now(timezone.utc).isoformat(), event=event, **values)) + '\n')

    def observe(candidate, diagnostic_only=False):
        snapshot, _ = store_snapshot(sb, store)
        log('before_product', product_id=candidate['item_id'], diagnostic_only=diagnostic_only, **snapshot)
        page = fetch_product(sb, candidate['url'], settings,
                             capture=make_capture(output / 'captures', 'same-session', state))
        try:
            product = next_data(page).get('data', {}).get('product') or {}
            context = product_context(product, store)
            row = dict(sequence=state['sequence'], diagnostic_only=diagnostic_only,
                       identity_matches=str(product.get('usItemId')) == candidate['item_id'],
                       listing_sequence=candidate.get('listing_sequence'),
                       price_context=product.get('priceInfo'), **context)
            report['observations'].append(row)
            save()
            if diagnostic_only:
                return row
            if not context['store_matches']:
                report['wrong_sequence'] = state['sequence']
                # Same session, exact URL/options, one retry for evidence only.
                try:
                    corrected = observe(candidate, diagnostic_only=True)
                    report['pair_captured'] = corrected['store_matches'] and corrected['identity_matches']
                    report['refetch_sequence'] = corrected['sequence']
                except Exception as error:
                    report['refetch_error'] = str(error)
                raise ValueError('Store drift: run invalidated; re-fetch cannot rehabilitate it')
            if not row['identity_matches']:
                raise ValueError('Product identity mismatch')
            record, reason, _ = product_record(candidate, page, store, settings['private_labels'], logo)
            row['acceptance_reason'] = reason
            if record is not None:
                report['accepted'].append(record)
            time.sleep(settings['delay_seconds'])
            return row
        finally:
            page.decompose()

    def timeout(*_):
        raise TimeoutError(f"{limits['seconds']}-second diagnostic limit reached")

    prior = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(limits['seconds'])
    save()
    try:
        sb = open_browser()
        logo = select_store(sb, store, settings, log, output)
        seen = set()
        for category, path, limit in cases:
            url = 'https://www.walmart.com/browse/' + path
            remaining = limit
            page_limit = page_limits.get(category, pages if category in ['Balloons', 'Diapering'] else 1)
            for _ in range(page_limit):
                report['category_visits'] += 1
                log('category_visit', category=category, url=safe_url(url))
                page = navigate(sb, url, settings, log)
                try:
                    verify_banner(page, store)
                    native_next, native_context = None, None
                    if rendered:
                        native_next, native_context = rendered_next(
                            sb, url, store, output / f"rendered-{report['category_visits']}.html", log)
                finally:
                    page.decompose()
                page = fetch_product(sb, url, settings,
                                     capture=make_capture(output / 'captures', 'same-session', state, 'listing'))
                try:
                    if rendered_cards:
                        candidates, rejected, search = listing_from_rendered(
                            output / f"rendered-{report['category_visits']}.html", page, category, store)
                    else:
                        candidates, rejected, search = listing_candidates(page, category, store)
                    listing_sequence = state['sequence']
                    report['listings'].append(dict(sequence=listing_sequence, category=category,
                                                   candidate_ids=[c['item_id'] for c in candidates],
                                                   rendered_snapshot=f"rendered-{report['category_visits']}.html" if rendered_cards else None))
                    props = ((search or {}).get('paginationV2') or {}).get('pageProperties') or {}
                    log('listing_context', sequence=state['sequence'], store=props.get('stores'),
                        facet=props.get('facet'), candidates=len(candidates), excluded=len(rejected))
                    verify_listing_store(search, store)
                    following = next_page_url(page, url, search) or native_next
                    pagination = (search or {}).get('paginationV2') or {}
                    current_page = int(props.get('page') or 1)
                    if native_context and native_context['page'] != current_page:
                        raise ValueError('Rendered and fetched listing page identifiers differ')
                    more_reported = current_page < int(pagination.get('maxPage') or 1)
                finally:
                    page.decompose()
                selected = [c for c in candidates if c['item_id'] not in seen]
                # The previously rejected item is tested first if present in today's listing.
                if category == 'Household Essentials':
                    selected.sort(key=lambda c: c['item_id'] != '857115210')
                for candidate in selected[:remaining]:
                    seen.add(candidate['item_id'])
                    candidate['listing_sequence'] = listing_sequence
                    observe(candidate)
                    remaining -= 1
                save()
                if not following and more_reported and remaining and page_limit > 1:
                    report['pagination_gaps'].append(dict(category=category, page=current_page,
                                                         reason='More pages reported but no observed next-page control'))
                if remaining == 0 or not following:
                    break
                url = following
        report['attempt_finished'] = True
        report['completed'] = not report['pagination_gaps']
    except Exception as error:
        report.update(error=str(error), error_type=type(error).__name__)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prior)
        if sb:
            sb.quit()
        save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--pages', type=int, choices=[1, 3], default=1)
    parser.add_argument('--rendered-pagination', action='store_true')
    parser.add_argument('--extended', action='store_true', help='One historical-length probe: up to70 targets/20 listings')
    parser.add_argument('--rendered-candidates', action='store_true')
    parser.add_argument('--artsets', action='store_true', help='One page/up to5products/180seconds')
    args = parser.parse_args()
    os.umask(0o077)
    result = run(args.output, args.pages, args.rendered_pagination, args.extended, args.rendered_candidates, args.artsets)
    print(json.dumps({key: result.get(key) for key in ['completed', 'pair_captured', 'counts', 'seconds', 'error']}))
