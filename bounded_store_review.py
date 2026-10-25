"""Prepare or execute one private, bounded session comparison. No production publication."""
import argparse
import hashlib
import json
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from browser import open_browser, select_store, navigate, verify_banner, fetch_product, store_snapshot
from diagnostic_capture import make_capture, safe_url
from extract import listing_candidates, next_data, pickup, product_record
from scrape import verify_listing_store
from storage import atomic_json
from trace_store_context import product_context


def sessions(cases, repeats=2):
    result = []
    for repeat in range(1, repeats + 1):
        result.append({'id': f'A{repeat}', 'mode': 'existing_session', 'cases': cases})
        for index in [0, 1]:
            result.append({'id': f'B{repeat}-{index + 1}', 'mode': 'fresh_small_batch',
                           'cases': cases[index * 3:index * 3 + 3]})
    return result


def private_folder(output):
    output = Path(output).resolve()
    if not output.is_relative_to(Path('data').resolve()):
        raise ValueError('Diagnostic output must stay under ignored data/')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    return output


def run(plan, output):
    if len(plan['cases']) != 6 or len({c['item_id'] for c in plan['cases']}) != 6:
        raise ValueError('Comparison requires six distinct planned products')
    if not 0 < plan['limits']['product_requests'] <= 36 or not 0 < plan['limits']['listing_requests'] <= 8 or not 0 < plan['limits']['seconds'] <= 2400:
        raise ValueError('Plan exceeds approved diagnostic limits')
    output = private_folder(output)
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = next(s for s in settings['stores'] if str(s['id']) == '100')
    limits = plan['limits']
    state = {'started': time.monotonic(), 'limits': limits, 'product_requests': 0,
             'listing_requests': 0, 'sequence': 0, 'body_bytes': 0, 'category_visits': 0, 'browser_sessions': 0}
    state.update(plan.get('counts_before', {}))
    report = {'mode': 'bounded live diagnostic; never publishes production data', 'sessions': [],
              'observations': [], 'completed': False, 'store_mismatch_seen': False,
              'plan': plan, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'code_sha256': {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                              for p in ['browser.py', 'diagnostic_capture.py', 'bounded_store_review.py',
                                        'extract.py', 'scrape.py', 'config/stores.json']}}
    sb = None
    active = None
    current = None

    def save():
        report['counts'] = {key: state[key] for key in ['product_requests', 'listing_requests', 'sequence',
                                                       'body_bytes', 'category_visits', 'browser_sessions']}
        report['counts_this_run'] = {key: value - plan.get('counts_before', {}).get(key, 0)
                                    for key, value in report['counts'].items()}
        report['seconds'] = round(time.monotonic() - state['started'], 3)
        atomic_json(output / 'report.json', report)

    def log(event, **values):
        # No retailer cookie values or unfiltered browser metadata are logged.
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps({'time_utc': datetime.now(timezone.utc).isoformat(),
                                    'session': active['id'], 'event': event, **values}) + '\n')

    def observe(candidate, control=False, diagnostic_only=False):
        snapshot, _ = store_snapshot(sb, store)
        log('before_product', id=candidate['item_id'], **snapshot)
        page = fetch_product(sb, candidate['url'], settings,
                             capture=make_capture(output / 'captures', active['id'], state))
        try:
            product = next_data(page).get('data', {}).get('product') or {}
            context = product_context(product, store)
            row = {'session': active['id'], 'sequence': state['sequence'], 'control': control,
                   'diagnostic_only': diagnostic_only, **context,
                   'price_context': product.get('priceInfo'),
                   'identity_matches': str(product.get('usItemId')) == candidate['item_id']}
            report['observations'].append(row)
            save()
            if diagnostic_only:
                return  # Evidence only; cannot rehabilitate the rejected run.
            if not context['store_matches']:
                report['store_mismatch_seen'] = True
                raise ValueError('Location mismatch or missing response context; diagnostic invalidated')
            if not row['identity_matches']:
                raise ValueError('Product identity mismatch')
            if control:
                if not pickup(product, store) or (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart', 'Walmart.com']:
                    raise ValueError('Control lacks local pickup/Walmart seller evidence')
            else:
                record, reason, _ = product_record(candidate, page, store, settings['private_labels'], active['logo'])
                row['acceptance_reason'] = reason
                if record is None:
                    raise ValueError('Product not accepted: ' + reason)
                active['accepted'].append(record)
            time.sleep(settings['delay_seconds'])
        finally:
            page.decompose()

    def timeout(*_):
        raise TimeoutError('Diagnostic runtime limit reached')

    prior = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(limits['seconds'])
    save()
    try:
        for session in sessions(plan['cases'], plan.get('comparison_repeats', 2)):
            if state['browser_sessions'] >= 6:
                raise RuntimeError('Diagnostic browser-session budget reached')
            current = None
            active = {**session, 'accepted': [], 'passed': False}
            report['sessions'].append(active)
            folder = output / active['id']
            folder.mkdir()
            log('session_started', mode=active['mode'])
            state['browser_sessions'] += 1
            sb = open_browser()
            initial, _ = store_snapshot(sb, store)
            log('fresh_session_before_selection', **initial)
            active['logo'] = select_store(sb, store, settings, log, folder)
            control_url = store['canary_urls'][0]
            control = {'url': control_url, 'item_id': control_url.split('?')[0].rstrip('/').split('/')[-1]}
            current = control
            observe(control, control=True)
            listing_url = None
            for case in active['cases']:
                if case['listing_url'] != listing_url:
                    current = None
                    if state['category_visits'] >= 8:
                        raise RuntimeError('Diagnostic category-visit budget reached')
                    state['category_visits'] += 1
                    listing_url = case['listing_url']
                    log('category_visit', url=safe_url(listing_url), category=case['category'])
                    page = navigate(sb, listing_url, settings, log)
                    verify_banner(page, store)
                    page.decompose()
                    page = fetch_product(sb, listing_url, settings,
                                         capture=make_capture(output / 'captures', active['id'], state, 'listing'))
                    try:
                        candidates, _, search = listing_candidates(page, case['category'], store)
                        verify_listing_store(search, store)
                        props = ((search or {}).get('paginationV2') or {}).get('pageProperties') or {}
                        if str(props.get('stores') or '') != str(store['id']):
                            raise ValueError('Listing store context missing or unverifiable')
                        if 'fulfillment_method:Pickup' not in str(props.get('facet') or ''):
                            raise ValueError('Listing pickup context missing or unverifiable')
                        log('listing_context', store=str(props['stores']), facet=props.get('facet'),
                            sequence=state['sequence'], candidate_ids=[c['item_id'] for c in candidates])
                    finally:
                        page.decompose()
                candidate = next((c for c in candidates if c['item_id'] == case['item_id']), None)
                if candidate is None:
                    raise ValueError('Planned product absent from verified current listing')
                current = candidate
                observe(candidate)
            current = control
            observe(control, control=True)
            active['passed'] = True
            log('session_completed', accepted=len(active['accepted']))
            sb.quit()
            sb = None
            save()
        report['completed'] = True
    except Exception as error:
        if 'Location mismatch' in str(error) or 'Listing store context' in str(error):
            report['store_mismatch_seen'] = True
        report['error'] = str(error)
        report['error_type'] = type(error).__name__
        # A single evidence re-fetch is allowed only after product-context drift.
        if report['store_mismatch_seen'] and current and sb:
            try:
                observe(current, diagnostic_only=True)
            except Exception as probe_error:
                report['probe_error'] = str(probe_error)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prior)
        if sb:
            sb.quit()
        save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', default='config/diagnostic-20261025.json')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--live', action='store_true', help='Actually contact retailer; omitted means plan only')
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text())
    if args.live:
        os.umask(0o077)
        result = run(plan, args.output)
        print(json.dumps({'completed': result['completed'], 'counts': result['counts'], 'error': result.get('error')}))
        if not result['completed']:
            raise SystemExit(1)
    else:
        print(json.dumps({'mode': 'plan only; no browser or requests', 'sessions': sessions(plan['cases'], plan.get('comparison_repeats', 2)),
                          'limits': plan['limits']}, indent=2))
