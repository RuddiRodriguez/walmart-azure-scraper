"""One bounded cross-category collection. Review output only; never production publication."""
import argparse
import csv
import hashlib
import json
import os
import re
import signal
import subprocess
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from browser import open_browser, select_store, navigate, verify_banner, fetch_product
from capture_store_drift import listing_from_rendered
from diagnostic_capture import make_capture, safe_url
from extract import category_id, discover, next_data, pickup, product_record
from scrape import next_page_url, verify_listing_store
from storage import atomic_json, page_url
from trace_store_context import product_context
from validate import validate


LIMITS = dict(product_requests=750, listing_requests=80, seconds=3600)


def run(output, plan):
    if any(not 0 < plan['limits'][key] <= value for key, value in LIMITS.items()):
        raise ValueError('Plan exceeds controlled request/runtime limits')
    if not 0 < plan['target'] <= 550 or plan['minimum_per_category'] < 1:
        raise ValueError('Invalid controlled sample target')
    output = Path(output).absolute()
    if not output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Evidence must stay under ignored data/')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = settings['stores'][0]
    state = dict(started=time.monotonic(), limits=plan['limits'], product_requests=0,
                 listing_requests=0, sequence=0, body_bytes=0, body_limit_bytes=1024 * 2**20)
    names = [c['category'] for c in plan['categories']]
    queues = {c['category']: deque(c['urls']) for c in plan['categories']}
    roots = {c['category']: c['required_root'] for c in plan['categories']}
    seen_pages, seen_products = set(), set()
    accepted, sources = {}, []
    counts = Counter()
    report = dict(mode='One bounded live cross-category review collection; not full uncapped coverage',
                  started_utc=datetime.now(timezone.utc).isoformat(), source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  source_hashes={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
                                 ['controlled_collection.py', 'diagnostic_capture.py', 'capture_store_drift.py', 'scrape.py', 'browser.py', 'extract.py', 'storage.py', 'validate.py']},
                  plan=plan, pages=[], observations=[], exclusions={}, completed_attempt=False,
                  target_reached=False, pair_captured=False, full_coverage_complete=False)
    sb = None

    def save():
        report['counts'] = {k: state[k] for k in ['product_requests', 'listing_requests', 'sequence', 'body_bytes']}
        report['accepted_records'] = len(accepted)
        report['category_counts'] = dict(counts)
        report['seconds'] = round(time.monotonic() - state['started'], 3)
        report['pending_pages'] = {name: len(queue) for name, queue in queues.items()}
        atomic_json(output / 'products.json', list(accepted.values()))
        report['unattempted_candidate_count'] = len({key for page in report['pages'] for key in page.get('candidate_ids', [])} - seen_products)
        atomic_json(output / 'report.json', report)

    def log(event, **values):
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(time_utc=datetime.now(timezone.utc).isoformat(), event=event, **values)) + '\n')

    def exclude(reason):
        report['exclusions'][reason] = report['exclusions'].get(reason, 0) + 1

    def observe(candidate, listing_sequence, diagnostic_only=False):
        page = fetch_product(sb, candidate['url'], settings,
                             capture=make_capture(output / 'captures', 'collection', state))
        try:
            data = next_data(page)
            product = data.get('data', {}).get('product') or {}
            context = product_context(product, store)
            observation = dict(sequence=state['sequence'], listing_sequence=listing_sequence,
                               identity_matches=str(product.get('usItemId')) == candidate['item_id'],
                               diagnostic_only=diagnostic_only, **context)
            report['observations'].append(observation)
            if diagnostic_only:
                return observation
            if not context['store_matches']:
                report['wrong_sequence'] = state['sequence']
                try:
                    corrected = observe(candidate, listing_sequence, diagnostic_only=True)
                    report['pair_captured'] = corrected['store_matches'] and corrected['identity_matches']
                    report['refetch_sequence'] = corrected['sequence']
                except Exception as error:
                    report['refetch_error'] = str(error)
                raise ValueError('Store drift: entire collection invalid for publication')
            if not observation['identity_matches']:
                raise ValueError('Product identity mismatch')
            row, reason, _ = product_record(candidate, page, store, settings['private_labels'], logo)
            observation['acceptance_reason'] = reason
            if row:
                accepted[candidate['item_id']] = row
                counts[candidate['category']] += 1
                source = dict(candidate=candidate, product=product,
                              specifications=(data.get('data', {}).get('idml') or {}).get('specifications'),
                              reason=reason, product_sequence=state['sequence'], listing_sequence=listing_sequence)
                sources.append(source)
                with (output / 'source-records.jsonl').open('a') as stream:
                    stream.write(json.dumps(source) + '\n')
            else:
                exclude(reason)
            save()
            time.sleep(settings['delay_seconds'])
        finally:
            page.decompose()

    def control():
        url = store['canary_urls'][0]
        page = fetch_product(sb, url, settings, capture=make_capture(output / 'captures', 'collection', state))
        try:
            product = next_data(page).get('data', {}).get('product') or {}
            if (not product_context(product, store)['store_matches'] or str(product.get('usItemId')) != '47428850'
                    or not pickup(product, store) or (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart', 'Walmart.com']):
                raise ValueError('Store control failed')
        finally:
            page.decompose()

    def timeout(*_):
        raise TimeoutError('Controlled collection runtime limit')

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(plan['limits']['seconds'])
    save()
    try:
        sb = open_browser()
        logo = select_store(sb, store, settings, log, output)
        control()
        report['initial_control_passed'] = True
        while any(queues.values()) and not (len(accepted) >= plan['target'] and all(counts[n] >= plan['minimum_per_category'] for n in names)):
            for name in names:
                if len(accepted) >= plan['target'] and all(counts[n] >= plan['minimum_per_category'] for n in names):
                    break
                if not queues[name]:
                    continue
                if state['listing_requests'] >= plan['limits']['listing_requests']:
                    raise RuntimeError('Listing budget reached')
                url = page_url(queues[name].popleft())
                if (name, url) in seen_pages:
                    log('page_skipped', category=name, url=safe_url(url), reason='already_visited')
                    continue
                seen_pages.add((name, url))
                entry = dict(category=name, url=safe_url(url), status='started', decisions=[])
                report['pages'].append(entry)
                save()
                native = navigate(sb, url, settings, log)
                try:
                    verify_banner(native, store)
                    stable, prior = 0, -1
                    for _ in range(20):
                        sb.scroll_down(900)
                        sb.sleep(0.4)
                        native.decompose()
                        native = BeautifulSoup(sb.get_page_source(), 'html.parser')
                        verify_banner(native, store)
                        visible = len(native.select('[data-item-id]'))
                        stable = stable + 1 if visible == prior else 0
                        prior = visible
                        if stable >= 4:
                            break
                    else:
                        raise ValueError('Listing lazy loading did not settle')
                    snapshot = output / f'native-{len(report["pages"])}.html'
                    body = str(native).encode()
                    snapshot.write_bytes(body)
                    entry.update(snapshot=snapshot.name, snapshot_sha256=hashlib.sha256(body).hexdigest())
                    native_search = next_data(native).get('searchResult')
                    native_next = next_page_url(native, url, native_search)
                    links = discover(native, roots[name], ['recipes', r'shop[- ]all[- ]foods?$', 'farm[- ]animals'],
                                     current_url=url, decisions=entry['decisions'])
                finally:
                    native.decompose()
                page = fetch_product(sb, url, settings, capture=make_capture(output / 'captures', 'collection', state, 'listing'))
                try:
                    listing_sequence = state['sequence']
                    search = next_data(page).get('searchResult')
                    if bool(native_search) != bool(search):
                        raise ValueError('Native and captured listing kinds differ')
                    if search:
                        candidates, rejected, search = listing_from_rendered(snapshot, page, name, store)
                        verify_listing_store(search, store)
                        following = next_page_url(page, url, search) or native_next
                        props = (search.get('paginationV2') or {}).get('pageProperties') or {}
                        if int(props.get('page') or 1) < int((search.get('paginationV2') or {}).get('maxPage') or 1) and not following:
                            raise ValueError('Reported next page lacks observed control')
                        if following:
                            queues[name].appendleft(following)
                    else:
                        candidates, rejected = [], []
                    for rejection in rejected:
                        exclude(rejection['reason'])
                    entry.update(listing_sequence=listing_sequence, candidate_ids=[c['item_id'] for c in candidates],
                                 rejected_candidates=rejected, status='reviewed')
                finally:
                    page.decompose()
                for link in links:
                    parent = category_id(roots[name])
                    uncertain_pet_branch = name == 'Pets' and '1092244' in category_id(link).split('_')
                    if re.search(r'(?:^|_)' + re.escape(parent) + r'(?:_|$)', category_id(link)) and '4519281' not in category_id(link).split('_') and not uncertain_pet_branch:
                        if (name, link) not in seen_pages:
                            queues[name].append(link)
                    else:
                        for decision in entry['decisions']:
                            if decision['url'] == link and decision['action'] == 'queued':
                                decision.update(action='not_crawled', reason='scope_unverified_or_known_empty_route')
                for candidate in candidates:
                    if len(accepted) >= plan['target'] and all(counts[n] >= plan['minimum_per_category'] for n in names):
                        break
                    if candidate['item_id'] in seen_products:
                        exclude('duplicate_product_id')
                        continue
                    # Leave room for a diagnostic re-fetch and final control.
                    if state['product_requests'] >= plan['limits']['product_requests'] - 2:
                        raise RuntimeError('Product budget reached')
                    seen_products.add(candidate['item_id'])
                    observe(candidate, listing_sequence)
                save()
        control()
        report['final_control_passed'] = True
        report['completed_attempt'] = True
        report['target_reached'] = len(accepted) >= plan['target'] and all(counts[n] >= plan['minimum_per_category'] for n in names)
    except Exception as error:
        report.update(error=str(error), error_type=type(error).__name__)
        if report['pages'] and report['pages'][-1]['status'] == 'started':
            report['pages'][-1].update(status='failed', error=str(error))
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
        if sb:
            sb.quit()
        atomic_json(output / 'source-records.json', sources)
        unavailable = {s['candidate']['url'] for s in sources if s['reason'] == 'retained_unavailable'}
        report['sample_validation'] = validate(list(accepted.values()), names, store,
            {**settings, 'minimum_records': plan['target'], 'minimum_category_records': plan['minimum_per_category']}, 0, 0, 0,
            unavailable_urls=unavailable)
        report['unvisited_categories'] = [n for n in names if not counts[n]]
        save()
    print(json.dumps({k: report.get(k) for k in ['target_reached', 'accepted_records', 'category_counts', 'seconds', 'error']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    run(args.output, json.loads(args.plan.read_text()))
