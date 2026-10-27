"""One bounded cross-category collection. Review output only; never production publication."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import retention
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from browser import open_browser, select_store, capture_navigation, capture_product_navigation, verify_banner, fetch_product
from capture_store_drift import listing_from_rendered
from diagnostic_capture import make_capture, safe_url
from extract import category_id, discover, next_data, pickup, product_record
from scrape import next_page_url, verify_listing_store
from storage import atomic_json, page_url, product_url
from trace_store_context import product_context
from validate import validate


LIMITS = dict(product_requests=750, listing_requests=80, seconds=3600)


def run(output, plan, resume=False):
    requested_plan = json.loads(json.dumps(plan))
    plan = {**plan, 'limits': dict(plan['limits'])}
    if plan.get('deadline_utc'):
        remaining = int(datetime.fromisoformat(plan['deadline_utc']).timestamp() - time.time())
        if remaining <= 0:
            raise ValueError('Original controlled collection deadline expired')
        plan['limits']['seconds'] = min(plan['limits']['seconds'], remaining)
    if any(not 0 < plan['limits'][key] <= value for key, value in LIMITS.items()):
        raise ValueError('Plan exceeds controlled request/runtime limits')
    if not 0 < plan['target'] <= 550 or plan['minimum_per_category'] < 1:
        raise ValueError('Invalid controlled sample target')
    output = Path(output).absolute()
    if not output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Evidence must stay under ignored data/')
    output.mkdir(parents=True, exist_ok=resume, mode=0o700)
    lock = (output / "run.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        lock.close()
        raise
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=25)
    store = settings['stores'][0]
    state = dict(started=time.monotonic(), limits=plan['limits'], product_requests=0,
                 listing_requests=0, sequence=0, body_bytes=0, body_limit_bytes=min(plan.get('body_limit_bytes', 1024 * 2**20), 1024 * 2**20))
    names = [c['category'] for c in plan['categories']]
    queues = {c['category']: deque(c['urls']) for c in plan['categories']}
    roots = {c['category']: c['required_root'] for c in plan['categories']}
    seen_pages, seen_products = set(), set()
    accepted, sources = {}, []
    counts = Counter()
    pending_products = deque()
    active_page = None
    report = dict(mode='One bounded live cross-category review collection; not full uncapped coverage',
                  started_utc=datetime.now(timezone.utc).isoformat(), source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  source_hashes={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
                                 ['controlled_collection.py', 'diagnostic_capture.py', 'capture_store_drift.py', 'scrape.py', 'browser.py', 'extract.py', 'storage.py', 'validate.py', 'retention.py']},
                  plan=plan, pages=[], observations=[], controls=[], failures=[], exclusions={}, completed_attempt=False,
                  target_reached=False, pair_captured=False, full_coverage_complete=False)
    signature = hashlib.sha256(json.dumps(dict(plan=requested_plan, source=report['source_hashes'],
        stores=Path('config/stores.json').read_text(), categories=Path('config/categories.csv').read_text(),
        requirements=Path('requirements.txt').read_text()), sort_keys=True).encode()).hexdigest()
    try:
        if resume:
            checkpoint = json.loads((output / 'checkpoint.json').read_text())
            if checkpoint['signature'] != signature:
                raise ValueError('Code or settings changed; start a fresh run')
            report = checkpoint['report']
            if report['completed_attempt']:
                raise ValueError('Bounded attempt already completed; no resume work')
            elapsed = time.time() - datetime.fromisoformat(report['started_utc']).timestamp()
            plan = report['plan']
            if elapsed >= plan['limits']['seconds']:
                raise ValueError('Original collection deadline expired')
            state.update(started=time.monotonic() - elapsed, limits=plan['limits'])
            queues = {name: deque(values) for name, values in checkpoint['queues'].items()}
            seen_pages = {tuple(value) for value in checkpoint['seen_pages']}
            seen_products = set(checkpoint['seen_products'])
            accepted = checkpoint['accepted']
            counts = Counter(row['category'] for row in accepted.values())
            pending_products = deque(checkpoint['pending_products'])
            lines = (output / 'source-records.jsonl').read_text().splitlines() if (output / 'source-records.jsonl').exists() else []
            sources = [json.loads(line) for line in lines[:checkpoint['source_count']]]
            if len(sources) != len(accepted):
                raise ValueError('Committed source/record count mismatch')
            with (output / 'source-records.jsonl').open('w') as stream:
                stream.write(''.join(json.dumps(source) + '\n' for source in sources))
                stream.flush()
                os.fsync(stream.fileno())
            active_page = checkpoint['active_page']
            if active_page:
                name, url = active_page['category'], active_page['url']
                queues[name].appendleft(url)
                seen_pages.discard((name, url))
                report['pages'][-1]['status'] = 'interrupted_uncommitted'
                active_page = None
            captures = [json.loads(path.read_text()) for path in (output / 'captures').glob('*.json')]
            state['product_requests'] = sum(c['kind'] == 'product' for c in captures)
            state['listing_requests'] = sum(c['kind'] == 'listing' for c in captures)
            state['sequence'] = max((c['sequence'] for c in captures), default=0)
            state['body_bytes'] = sum(p.stat().st_size for p in (output / 'captures').glob('*.body'))
            report['resume_count'] = report.get('resume_count', 0) + 1
            report.pop('error', None)
            report.pop('error_type', None)
    except Exception:
        lock.close()
        raise
    catalog = retention.connect(plan.get('catalog_path', f"data/catalog/store-{store['id']}.sqlite"), store)
    report['retention_mode'] = 'store-history-v1'
    sb = None

    def save():
        report['counts'] = {k: state[k] for k in ['product_requests', 'listing_requests', 'sequence', 'body_bytes']}
        report['accepted_records'] = len(accepted)
        report['rejected_product_responses'] = sum(bool(o.get('acceptance_reason')) and not o['acceptance_reason'].startswith('retained_') for o in report['observations'])
        report['retained_response_reasons'] = dict(Counter(o['acceptance_reason'] for o in report['observations'] if str(o.get('acceptance_reason', '')).startswith('retained_')))
        report['product_errors'] = sum(f['kind'] == 'product' for f in report['failures'])
        report['page_errors'] = sum(f['kind'] in ['page', 'page_processing'] for f in report['failures'])
        report['category_counts'] = dict(counts)
        report['seconds'] = round(time.monotonic() - state['started'], 3)
        report['pending_pages'] = {name: len(queue) for name, queue in queues.items()}
        atomic_json(output / 'products.json', list(accepted.values()))
        report['unattempted_candidate_count'] = len({key for page in report['pages'] for key in page.get('candidate_ids', [])} - seen_products)
        atomic_json(output / 'report.json', report)
        atomic_json(output / 'checkpoint.json', dict(signature=signature, report=report,
            queues={name: list(queue) for name, queue in queues.items()},
            seen_pages=sorted(seen_pages), seen_products=sorted(seen_products),
            accepted=accepted, source_count=len(sources), pending_products=list(pending_products), active_page=active_page))

    def log(event, **values):
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(time_utc=datetime.now(timezone.utc).isoformat(), event=event, **values)) + '\n')

    def exclude(reason):
        report['exclusions'][reason] = report['exclusions'].get(reason, 0) + 1

    def fatal(error):
        message = str(error).lower()
        return any(word in message for word in ['store control', 'access blocked', 'challenge', 'evidence capture',
            'budget reached', 'body budget', 'disk reserve', 'runtime limit', 'failure ceiling'])

    def failure(kind, error, **values):
        report['failures'].append(dict(kind=kind, reason=str(error), error_type=type(error).__name__, **values))
        log('failed_once', kind=kind, reason=str(error), **values)
        if fatal(error) or len(report['failures']) >= plan.get('maximum_ordinary_failures', 10):
            raise RuntimeError('Failure ceiling reached or unsafe context: ' + str(error)) from error

    def observe(candidate, listing_sequence):
        page = capture_product_navigation(
            sb, product_url(candidate['url']), settings, log,
            make_capture(output / 'captures', 'collection', state))
        try:
            data = next_data(page)
            product = data.get('data', {}).get('product') or {}
            context = product_context(product, store)
            observation = dict(sequence=state['sequence'], listing_sequence=listing_sequence,
                               identity_matches=str(product.get('usItemId')) == candidate['item_id'],
                               diagnostic_only=False, **context)
            report['observations'].append(observation)
            reason = ('wrong_store_context' if not context['store_matches'] else
                      'product_identity_mismatch' if not observation['identity_matches'] else '')
            capture_path = output / 'captures' / f"collection-{state['sequence']:03}.json"
            capture_meta = json.loads(capture_path.read_text()) if capture_path.exists() else {}
            observed_utc = (capture_meta.get('response') or {}).get('received_utc') or (capture_meta.get('request') or {}).get('started_utc') or datetime.now(timezone.utc).isoformat()
            source_key = str(output.relative_to(Path.cwd())) + '#' + str(state['sequence'])
            if reason:
                retention.observe(catalog, candidate['item_id'], None, reason, source_key, observed_utc, False)
                observation['acceptance_reason'] = reason
                exclude(reason)
                log('response_rejected', product_id=candidate['item_id'], sequence=state['sequence'], reason=reason)
                time.sleep(settings['delay_seconds'])
                return
            known = retention.known_assortment(catalog, candidate['item_id'])
            row, reason, _ = product_record(candidate, page, store, settings['private_labels'], logo, retain_missing=True, known_store_assortment=known)
            eligibility = reason != 'retained_assortment_unverified'
            state_name = retention.product_state(candidate, product, store, known, reason) if row else reason
            row = retention.observe(catalog, candidate['item_id'], row, state_name, source_key, observed_utc, eligibility if row else False)
            observation['acceptance_reason'] = reason
            if row and eligibility:
                accepted[candidate['item_id']] = row
                counts[candidate['category']] += 1
                source = dict(candidate=candidate, product=product,
                              specifications=(data.get('data', {}).get('idml') or {}).get('specifications'),
                              reason=reason, product_sequence=state['sequence'], listing_sequence=listing_sequence, known_store_assortment=known)
                sources.append(source)
                with (output / 'source-records.jsonl').open('a') as stream:
                    stream.write(json.dumps(source) + '\n')
                    stream.flush()
                    os.fsync(stream.fileno())
            else:
                exclude(reason)
            time.sleep(settings['delay_seconds'])
        finally:
            page.decompose()

    def collect_pending():
        while pending_products:
            if len(accepted) >= plan['target'] and all(counts[n] >= plan['minimum_per_category'] for n in names):
                break
            job = pending_products[0]
            candidate, listing_sequence = job['candidate'], job['listing_sequence']
            key = candidate['item_id']
            if key in seen_products:
                exclude('duplicate_product_id')
            elif key in plan.get('quarantined_product_ids', []):
                exclude('prior_wrong_store_product_quarantined')
            else:
                if state['product_requests'] >= plan['limits']['product_requests'] - 2:
                    raise RuntimeError('Product budget reached')
                log('product_started', product_id=key, category=candidate['category'])
                try:
                    observe(candidate, listing_sequence)
                except Exception as error:
                    failure('product', error, product_id=key, category=candidate['category'])
                    exclude('product_exception')
            seen_products.add(key)
            pending_products.popleft()
            save()
            log('product_committed', product_id=key, accepted=key in accepted)

    def control(stage):
        url = store['canary_urls'][0]
        page = None
        try:
            page = fetch_product(sb, url, settings, capture=make_capture(output / 'captures', 'collection', state))
            product = next_data(page).get('data', {}).get('product') or {}
            context = product_context(product, store)
            passed = (context['store_matches'] and str(product.get('usItemId')) == '47428850'
                      and pickup(product, store) and (product.get('sellerName') or product.get('sellerDisplayName')) in ['Walmart', 'Walmart.com'])
            report['controls'].append(dict(stage=stage, sequence=state['sequence'], passed=passed, **context))
            if not passed:
                exclude('control_context_rejected')
                log('control_rejected', stage=stage, sequence=state['sequence'])
            return passed
        except Exception as error:
            failure('control', error, stage=stage)
            report['controls'].append(dict(stage=stage, sequence=state['sequence'], passed=False, error_type=type(error).__name__))
            return False
        finally:
            if page:
                page.decompose()

    def timeout(*_):
        raise TimeoutError('Controlled collection runtime limit')

    previous = signal.signal(signal.SIGALRM, timeout)
    remaining_seconds = int(plan['limits']['seconds'] - (time.monotonic() - state['started']))
    signal.alarm(max(1, remaining_seconds))
    save()
    try:
        sb = open_browser()
        logo = select_store(sb, store, settings, log, output)
        log('session_started', resume=resume, committed_records=len(accepted))
        if resume:
            report['resume_control_passed'] = control('resume')
        else:
            report['initial_control_passed'] = control('initial')
        collect_pending()
        while any(queues.values()) and not (len(accepted) >= plan['target'] and all(counts[n] >= plan['minimum_per_category'] for n in names)):
            for name in names:
                if len(accepted) >= plan['target'] and all(counts[n] >= plan['minimum_per_category'] for n in names):
                    break
                if not queues[name]:
                    continue
                if state['listing_requests'] >= plan['limits']['listing_requests'] or len(report['pages']) >= plan['limits']['listing_requests']:
                    raise RuntimeError('Listing budget reached')
                url = page_url(queues[name].popleft())
                if (name, url) in seen_pages:
                    log('page_skipped', category=name, url=safe_url(url), reason='already_visited')
                    continue
                seen_pages.add((name, url))
                active_page = dict(category=name, url=url)
                entry = dict(category=name, url=safe_url(url), status='started', decisions=[])
                report['pages'].append(entry)
                save()
                try:
                    native, page = capture_navigation(
                        sb, url, settings, log,
                        make_capture(output / 'captures', 'collection', state, 'listing'))
                    try:
                        banner_verified = False
                        if native.select_one('[data-automation-id="fulfillment-banner"]'):
                            verify_banner(native, store)
                            banner_verified = True
                        stable, prior = 0, -1
                        for _ in range(20):
                            sb.scroll_down(900)
                            sb.sleep(0.4)
                            native.decompose()
                            native = BeautifulSoup(sb.get_page_source(), 'html.parser')
                            if native.select_one('[data-automation-id="fulfillment-banner"]'):
                                verify_banner(native, store)
                                banner_verified = True
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
                        entry.update(snapshot=snapshot.name, snapshot_sha256=hashlib.sha256(body).hexdigest(),
                                     native_banner_verified=banner_verified)
                        log('listing_banner_context', category=name, url=safe_url(url), verified=banner_verified,
                            reason='matching_store_pickup' if banner_verified else 'navigation_only_context_unavailable')
                        native_search = next_data(native).get('searchResult')
                        native_next = next_page_url(native, url, native_search)
                        links = discover(native, roots[name], ['recipes', r'shop[- ]all[- ]foods?$', 'farm[- ]animals'],
                                         current_url=url, decisions=entry['decisions'])
                    finally:
                        native.decompose()
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
                    pending_products.extend(dict(candidate=c, listing_sequence=listing_sequence) for c in candidates)
                    active_page = None
                    save()  # Commit page discovery and pending work together before product requests.
                    collect_pending()
                except Exception as error:
                    if entry['status'] == 'started':
                        entry.update(status='failed', error=str(error))
                        failure('page', error, category=name, url=safe_url(url))
                        active_page = None
                        save()
                    else:
                        if fatal(error):
                            raise
                        entry['processing_error'] = str(error)
                        failure('page_processing', error, category=name, url=safe_url(url))
                        save()
        report['final_control_passed'] = control('final')
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
        unavailable = {s['candidate']['url'] for s in sources if s['reason'] in ['retained_unavailable', 'retained_no_pickup_offer']}
        unknown_prices = {s['candidate']['url'] for s in sources if s['reason'].startswith('retained_') and s['candidate']['url'] not in unavailable}
        report['sample_validation'] = validate(list(accepted.values()), names, store,
            {**settings, 'minimum_records': plan['target'], 'minimum_category_records': plan['minimum_per_category']}, 0, 0, 0,
            unavailable_urls=unavailable, unknown_price_urls=unknown_prices)
        report['unvisited_categories'] = [n for n in names if not counts[n]]
        report['retention_catalog'] = retention.export(catalog, output)
        catalog.close()
        save()
        lock.close()
    print(json.dumps({k: report.get(k) for k in ['target_reached', 'accepted_records', 'category_counts', 'seconds', 'error']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    run(args.output, json.loads(args.plan.read_text()), args.resume)
