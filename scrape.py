"""Run a store crawl. --sample is evidence-only; it never replaces production output."""
import argparse
import csv
from collections import Counter
import fcntl
import hashlib
import json
import re
import time
import retention
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

from bs4 import BeautifulSoup

from browser import open_browser, select_store, navigate, verify_banner, fetch_product, canary_check, store_snapshot
from extract import discover, listing_candidates, listing_record, next_data, product_record
from storage import connect, metadata, atomic_json, add_pages, save_page, save_product, records, page_url
from validate import validate


def next_page_url(soup, current_url, search=None):
    link = soup.select_one('a[aria-label="Next Page"]')
    href = (link.get('href') or '').strip() if link else ''
    if href and not href.startswith(('#', 'javascript:')):
        return page_url(urljoin(current_url, href))
    if not link or not search:
        return ''
    # Current buttons carry the next page explicitly; URL shape was observed live.
    pagination = search.get('paginationV2') or {}
    current = int((pagination.get('pageProperties') or {}).get('page') or 1)
    extras = json.loads(link.get('data-dca-extras') or '{}')
    target = next((int(item['value']) for item in extras.get('custom', [])
                   if item.get('owner') == 'search' and item.get('name') == 'paginationPage'), 0)
    if target != current + 1 or target > int(pagination.get('maxPage') or 1):
        return ''
    parts = urlsplit(current_url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != 'page']
    query.append(('page', str(target)))
    return page_url(urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), '')))


def verify_listing_store(search, store, require_context=True):
    props = ((search or {}).get('paginationV2') or {}).get('pageProperties') or {}
    actual_store = str(props.get('stores') or '')
    intents = set(re.findall(r'fulfillment_method:([^|,;\s]+)', str(props.get('facet') or '')))
    if actual_store and actual_store != str(store['id']):
        raise ValueError('Location mismatch in primary listing store context')
    if intents and intents != {'Pickup'}:
        raise ValueError('Location mismatch in primary listing fulfillment context')
    verified = actual_store == str(store['id']) and intents == {'Pickup'}
    if require_context and not verified:
        raise ValueError('Location mismatch: primary listing store/Pickup context missing')
    return verified


def run(args):
    settings = json.loads(Path(args.config).read_text())
    store = next(s for s in settings['stores'] if str(s['id']) == args.store)
    configs = list(csv.DictReader(Path(args.categories).open()))
    categories = {c['Category (Auto)']: c for c in configs}
    base = Path(args.output).resolve() / args.store
    base.mkdir(parents=True, exist_ok=True)
    lock = (base / 'run.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    active = base / ('active-sample.json' if args.sample else 'active.json')
    if args.resume:
        if not active.exists():
            raise ValueError('No checkpoint to resume')
        run_id = json.loads(active.read_text())['run_id']
    else:
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        atomic_json(active, {'run_id': run_id})
    output = base / 'runs' / run_id
    output.mkdir(parents=True, exist_ok=True)
    (output / 'sources').mkdir(exist_ok=True)
    db = connect(output / 'checkpoint.sqlite')
    code = ''.join((Path(__file__).parent / name).read_text() for name in ['scrape.py', 'browser.py', 'extract.py', 'storage.py', 'validate.py', 'retention.py'])
    signature = hashlib.sha256((Path(args.config).read_text() + Path(args.categories).read_text() + str(args.sample) + code).encode()).hexdigest()
    if args.resume and metadata(db, 'signature') != signature:
        raise ValueError('Configuration or code changed; start a fresh run')
    if args.resume and time.time() - metadata(db, 'started') > settings['max_checkpoint_age_hours'] * 3600:
        raise ValueError('Checkpoint too old; start a fresh run to avoid stale prices')
    if not args.resume:
        metadata(db, 'signature', signature)
        metadata(db, 'started', time.time())
        metadata(db, 'active_seconds', 0)
        with db:
            for category, config in categories.items():
                add_pages(db, category, [config['URL']])
    unclean_resume = bool(metadata(db, 'session_open'))
    if unclean_resume:
        metadata(db, 'active_time_incomplete', True)
    metadata(db, 'session_open', True)
    started = time.monotonic()
    def log(event, **values):
        message = {'time': datetime.now(timezone.utc).isoformat(), 'event': event, 'store': args.store, **values}
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(message) + '\n')
        print(json.dumps(message), flush=True)
    log('run_started', run_id=run_id, resume=args.resume, unclean_resume=unclean_resume, signature=signature)
    sb = None
    current_work = {}
    sample_counts = Counter(row['category'] for row in records(db))
    catalog = retention.connect(base / 'catalog.sqlite', store)
    if (base / 'latest.json').exists():
        previous_pointer = json.loads((base / 'latest.json').read_text())
        if previous_pointer.get('products'):
            previous_products = base / previous_pointer['products']
            retention.seed_previous(catalog, json.loads(previous_products.read_text()), store, str(previous_products.relative_to(base)))
    prior_store_cookies = None

    def trace_context(stage):
        nonlocal prior_store_cookies
        if settings.get('trace_store_context'):
            snapshot, prior_store_cookies = store_snapshot(sb, store, prior_store_cookies)
            log('store_context', stage=stage, **snapshot)

    def unsafe_context(error):
        return any(text in str(error) for text in ['Location mismatch', 'Location ZIP mismatch',
                                                    'Product identity mismatch or missing response'])

    def fatal_transport(error):
        return any(text in str(error).lower() for text in ['challenge', 'access denied', 'access blocked',
                                                            'captcha', 'disk reserve'])

    def reject_page(category, url, reason):
        with db:
            db.execute("UPDATE pages SET status='failed' WHERE category=? AND url=?", (category, url))
        log('page_rejected', category=category, url=url, reason=reason)

    def collect_products():
        nonlocal current_work
        for key, text in db.execute("SELECT id,data FROM candidates WHERE status='pending' ORDER BY rowid").fetchall():
            candidate = json.loads(text)
            if args.sample and sample_counts[candidate['category']] >= args.sample:
                continue
            current_work = {'kind': 'product', 'id': key, 'url': candidate['url'], 'category': candidate['category']}
            log('product_started', **current_work)
            trace_context('before_product_' + key)
            cached = retention.current_record(catalog, key)
            row, reason = listing_record(candidate, cached, store, settings['private_labels'], logo)
            if row is not None:
                observed_utc = datetime.now(timezone.utc).isoformat()
                state = retention.product_state(candidate, candidate['item'], store, True, reason)
                row = retention.observe(catalog, key, row, state, run_id, observed_utc, True)
                save_product(db, candidate, row, reason)
                sample_counts[candidate['category']] += 1
                log('product', id=key, accepted=True, reason=reason, category=candidate['category'], source='verified_listing_with_cached_details')
                continue
            row = None
            reason = 'validation_error'
            source_data = {'candidate': candidate, 'reason': reason}
            for attempt in range(2):
                try:
                    soup = fetch_product(sb, candidate['url'], settings, log)
                    metadata(db, 'consecutive_transport_failures', 0)
                except Exception as error:
                    failures = (metadata(db, 'consecutive_transport_failures') or 0) + 1
                    metadata(db, 'consecutive_transport_failures', failures)
                    source_data.update(reason='transport_error', error=str(error), attempt=attempt + 1)
                    retention.observe(catalog, key, None, 'transport_error', run_id, datetime.now(timezone.utc).isoformat(), False)
                    save_product(db, candidate, None, 'transport_error', complete=False)
                    log('product_transport_error', id=key, failures=failures, error=str(error))
                    if fatal_transport(error) or failures >= settings.get('max_consecutive_transport_failures', 3):
                        raise RuntimeError('Repeated product transport failures; collection stopped') from error
                    reason = 'transport_error'
                    break
                data = next_data(soup).get('data') or {}
                source_data = {'candidate': candidate, 'product': data.get('product'),
                               'specifications': (data.get('idml') or {}).get('specifications'),
                               'reason': 'not_validated', 'attempt': attempt + 1}
                atomic_json(output / 'sources' / (key + '.json'), source_data)
                try:
                    known = retention.known_assortment(catalog, key)
                    row, reason, product = product_record(candidate, soup, store, settings['private_labels'], logo, retain_missing=True, known_store_assortment=known)
                    observed_utc = datetime.now(timezone.utc).isoformat()
                    row = retention.observe(catalog, key, row, retention.product_state(candidate, product, store, known, reason) if row else reason, run_id, observed_utc, bool(row and reason != 'retained_assortment_unverified'))
                    source_data['known_store_assortment'] = known
                    metadata(db, 'consecutive_context_failures', 0)
                    break
                except Exception as error:
                    context_error = unsafe_context(error)
                    failure_reason = 'unsafe_context' if context_error else 'validation_error'
                    retention.observe(catalog, key, None, failure_reason, run_id, datetime.now(timezone.utc).isoformat(), False)
                    source_data.update(reason=failure_reason, error=str(error))
                    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                    atomic_json(output / 'sources' / 'rejected' / (key + '-' + stamp + '.json'), source_data)
                    log('product_response_rejected', id=key, reason=failure_reason, attempt=attempt + 1)
                    try:
                        trace_context('rejected_product_' + key)
                    except Exception as trace_error:
                        log('store_trace_unavailable', error=str(trace_error))
                    if context_error:
                        metadata(db, 'location_mismatch_seen', True)
                        metadata(db, 'context_failures', (metadata(db, 'context_failures') or 0) + 1)
                        if attempt == 0:
                            canary_check(sb, store, settings)
                            log('product_context_retry', id=key, reason=str(error))
                            continue
                        failures = (metadata(db, 'consecutive_context_failures') or 0) + 1
                        metadata(db, 'consecutive_context_failures', failures)
                        reason = 'unsafe_context'
                        if failures >= settings.get('max_consecutive_context_failures', 3):
                            raise RuntimeError('Repeated unsafe store context; collection stopped') from error
                    save_product(db, candidate, None, reason,
                                 complete=reason not in {'transport_error', 'validation_error', 'unsafe_context'})
                    break
                finally:
                    soup.clear(decompose=True)
                    soup.decompose()
            source_data['reason'] = reason
            atomic_json(output / 'sources' / (key + '.json'), source_data)
            eligible_row = row if reason != 'retained_assortment_unverified' else None
            save_product(db, candidate, eligible_row, reason,
                         complete=bool(eligible_row) or reason not in {
                             'transport_error', 'validation_error', 'unsafe_context'})
            if eligible_row:
                sample_counts[candidate['category']] += 1
            log('product', id=key, accepted=bool(row), reason=reason, category=candidate['category'])
            time.sleep(settings['delay_seconds'])
        current_work = {}

    try:
        current_work = {'kind': 'store_selection'}
        sb = open_browser(headless=settings.get('headless', False))
        logo = select_store(sb, store, settings, log, output)
        trace_context('store_selected')
        canary_check(sb, store, settings)
        collect_products()
        page_count = db.execute("SELECT count(*) FROM pages WHERE status='done'").fetchone()[0]
        # Breadth-first across categories. Sample obtains a minimum from each category.
        page_limit_reached = False
        while True:
            order = "CASE WHEN url LIKE '%page=%' THEN 0 ELSE 1 END,CASE WHEN url LIKE '%/browse/%' THEN 0 ELSE 1 END,rowid"
            pending = db.execute("SELECT category,url FROM (SELECT category,url,rowid, row_number() OVER (PARTITION BY category ORDER BY " + order + ") AS position FROM pages WHERE status='pending') WHERE position=1 ORDER BY rowid").fetchall()
            if not pending:
                break
            progressed = False
            for category, url in pending:
                if args.sample:
                    if sample_counts[category] >= args.sample:
                        continue
                if page_count >= settings['max_pages']:
                    page_limit_reached = True
                    log('page_limit_reached', pages=page_count, pending=len(pending))
                    break
                current_work = {'kind': 'page', 'category': category, 'url': url}
                log('page_started', **current_work)
                try:
                    soup = navigate(sb, url, settings, log)
                    metadata(db, 'consecutive_transport_failures', 0)
                except Exception as error:
                    failures = (metadata(db, 'consecutive_transport_failures') or 0) + 1
                    metadata(db, 'consecutive_transport_failures', failures)
                    reject_page(category, url, 'transport_error')
                    if fatal_transport(error) or failures >= settings.get('max_consecutive_transport_failures', 3):
                        raise RuntimeError('Repeated listing transport failures; collection stopped') from error
                    continue
                verify_banner(soup, store)
                soup.clear(decompose=True)
                soup.decompose()
                trace_context('category_loaded')
                # Render lazy-loaded cards before matching structured data to visible offers.
                stable = 0
                prior_cards = -1
                for _ in range(60):
                    sb.scroll_down(900)
                    sb.sleep(0.5)
                    rendered = BeautifulSoup(sb.get_page_source(), 'html.parser')
                    card_count = len(rendered.select('[data-item-id]'))
                    rendered.clear(decompose=True)
                    rendered.decompose()
                    stable = stable + 1 if card_count == prior_cards else 0
                    prior_cards = card_count
                    if stable >= 4:
                        break
                else:
                    reject_page(category, url, 'lazy_loading_did_not_settle')
                    continue
                soup = BeautifulSoup(sb.get_page_source(), 'html.parser')
                verify_banner(soup, store)
                source = hashlib.sha256(url.encode()).hexdigest()[:20] + '.html'
                (output / 'sources' / source).write_text(str(soup))
                candidates, rejected, search = listing_candidates(soup, category, store)
                verified = verify_listing_store(search, store, require_context=bool(candidates))
                for candidate in candidates:
                    candidate['listing_store_verified'] = verified
                log('listing_context', verified=verified, candidates=len(candidates),
                    reason='matching_store_pickup' if verified else 'no_candidates_context_unverified')
                atomic_json(output / 'sources' / (source + '.listing.json'), {'category': category, 'url': url, 'rejected': rejected, 'candidate_ids': [c['item_id'] for c in candidates]})
                unresolved = [r for r in rejected if r['reason'] in ['not_rendered', 'missing_listing_fields', 'unexpected_product_url']]
                if unresolved:
                    log('listing_review_required', category=category, url=url, rejected=unresolved)
                if not args.sample and unresolved:
                    soup.clear(decompose=True)
                    soup.decompose()
                    reject_page(category, url, 'local_listing_records_need_review')
                    continue
                for candidate in candidates:
                    candidate['source'] = source
                exclusions = ['recipes', r'shop[- ]all[- ]foods?$', 'farm[- ]animals']
                links = discover(soup, categories[category]['URL'], exclusions, current_url=url, decisions=(decisions := []))
                next_link = soup.select_one('a[aria-label="Next Page"]')
                next_url = next_page_url(soup, sb.get_current_url() if search else url, search)
                has_next = bool(next_url)
                if next_link and not has_next:
                    decisions.append({'url': url, 'name': 'Next Page', 'action': 'skipped',
                                      'reason': 'placeholder_pagination_control'})
                    log('pagination_control_not_navigable', category=category, url=url)
                atomic_json(output / 'sources' / (source + '.links.json'), decisions)
                if has_next:
                    if next_url == url or db.execute("SELECT 1 FROM pages WHERE category=? AND url=? AND status='done'", (category, next_url)).fetchone():
                        soup.clear(decompose=True)
                        soup.decompose()
                        reject_page(category, url, 'pagination_loop')
                        continue
                    links[next_url] = 'Next Page'
                if search:
                    raw = sum(i.get('__typename') == 'Product' for stack in search.get('itemStacks', []) for i in stack.get('items', []))
                    pagination = search.get('paginationV2') or {}
                    current_page = int((pagination.get('pageProperties') or {}).get('page') or 1)
                    if raw == 0:
                        soup.clear(decompose=True)
                        soup.decompose()
                        reject_page(category, url, 'unexpected_zero_product_listing')
                        continue
                    if current_page < int(pagination.get('maxPage') or 1) and not has_next:
                        soup.clear(decompose=True)
                        soup.decompose()
                        reject_page(category, url, 'missing_next_page_control')
                        continue
                else:
                    raw = 0
                    if not links:
                        soup.clear(decompose=True)
                        soup.decompose()
                        reject_page(category, url, 'no_products_or_child_categories')
                        continue
                soup.clear(decompose=True)
                soup.decompose()
                save_page(db, category, url, links, candidates, rejected, raw)
                page_count += 1
                progressed = True
                log('category_page', category=category, url=url, raw=raw, local_candidates=len(candidates), discovered=len(links))
                collect_products()
                if page_count % 20 == 0:
                    canary_check(sb, store, settings)
            if page_limit_reached:
                break
            if not progressed:
                break
        canary_check(sb, store, settings)
        fresh_rows = records(db)
        rows = fresh_rows
        report_retention = retention.export(catalog, output)
        catalog_rows = json.loads((output / 'retained-products.json').read_text())
        catalog_states = {v['product_id']:v for v in json.loads((output / 'retention-status.json').read_text())}
        if not args.sample:
            rows = catalog_rows
        blank_price_urls = {r['url'] for r in rows if not r['regular_price']}
        unavailable_urls = {r['url'] for r in rows if catalog_states.get(r['url'].split('?')[0].rsplit('/',1)[-1], {}).get('state') in ['confirmed_unavailable','confirmed_no_pickup_offer']}
        unknown_price_urls = blank_price_urls - unavailable_urls
        pending_pages = db.execute("SELECT count(*) FROM pages WHERE status!='done'").fetchone()[0]
        pending_products = db.execute("SELECT count(*) FROM candidates WHERE status!='done'").fetchone()[0]
        review = db.execute("SELECT count(*) FROM candidates WHERE reason IN ('promotion_review_required','price_changed','unknown_availability')").fetchone()[0]
        previous = None
        if (base / 'latest.json').exists():
            pointer = json.loads((base / 'latest.json').read_text())
            previous = json.loads((base / pointer['report']).read_text())
        location_mismatch_seen = bool(metadata(db, 'location_mismatch_seen'))
        report = validate(rows, list(categories), store, settings, pending_pages, pending_products,
                          review, previous, unavailable_urls, unknown_price_urls,
                          location_mismatch_seen=location_mismatch_seen, fresh_rows=fresh_rows)
        if args.sample:
            sample_settings = {**settings, 'minimum_records': args.sample * len(categories), 'minimum_category_records': args.sample}
            report['sample_validation'] = validate(
                rows, list(categories), store, sample_settings, 0, 0, review,
                unavailable_urls=unavailable_urls, unknown_price_urls=unknown_price_urls,
                location_mismatch_seen=location_mismatch_seen, fresh_rows=fresh_rows)
        report.update(retention_catalog=report_retention, carried_observations=sum(v['source'] != run_id and v['assortment_confirmed'] for v in catalog_states.values()) if not args.sample else 0, location_mismatch_seen=location_mismatch_seen, mode='sample' if args.sample else 'full', store=store,
                      context_failures=metadata(db, 'context_failures') or 0,
                      page_limit_reached=page_limit_reached,
                      active_seconds=round(metadata(db, 'active_seconds') + time.monotonic() - started, 2),
                      elapsed_seconds=round(time.time() - metadata(db, 'started'), 2),
                      active_time_complete=not bool(metadata(db, 'active_time_incomplete')),
                      signature=signature, pages_processed=page_count,
                      duplicate_ids=db.execute('SELECT count(*)-count(DISTINCT id) FROM records').fetchone()[0],
                      exclusions=dict(db.execute('SELECT reason,sum(count) FROM exclusions GROUP BY reason')),
                      detail_exclusions=dict(db.execute("SELECT reason,count(*) FROM candidates WHERE reason!='' GROUP BY reason")))
        atomic_json(output / 'products.json', rows)
        atomic_json(output / 'report.json', report)
        if report['passed'] and not args.sample:
            atomic_json(base / 'latest.json', {'products': str((output / 'products.json').relative_to(base)), 'report': str((output / 'report.json').relative_to(base)), 'run_id': run_id})
            log('published', records=len(rows))
        else:
            log('not_published', mode=report['mode'], records=len(rows), errors=report['errors'])
        metadata(db, 'status', 'complete' if report['passed'] else 'review_required')
        if args.sample and not report['sample_validation']['passed']:
            raise RuntimeError('Sample failed validation; see report.json')
        if not args.sample and not report['passed']:
            raise RuntimeError('Full run failed publication checks; see report.json')
    except BaseException as error:
        if any(text in str(error) for text in ['Location mismatch', 'Location ZIP mismatch', 'Canary missing or incorrect store context']):
            metadata(db, 'location_mismatch_seen', True)
        # Keep reviewable partial output without changing the last successful publication.
        atomic_json(output / 'products.partial.json', records(db))
        atomic_json(output / 'failure.json', {
            'run_id': run_id, 'mode': 'sample' if args.sample else 'full',
            'active_seconds': round(metadata(db, 'active_seconds') + time.monotonic() - started, 2),
            'elapsed_seconds': round(time.time() - metadata(db, 'started'), 2),
            'active_time_complete': not bool(metadata(db, 'active_time_incomplete')),
            'signature': signature, 'location_mismatch_seen': bool(metadata(db, 'location_mismatch_seen')),
            'current_work': current_work, 'error': str(error), 'error_type': type(error).__name__,
            'records': len(records(db)),
            'pending_pages': db.execute("SELECT count(*) FROM pages WHERE status!='done'").fetchone()[0],
            'pending_products': db.execute("SELECT count(*) FROM candidates WHERE status!='done'").fetchone()[0],
            'published': False,
        })
        if sb:
            try:
                (output / 'failure-page.html').write_text(sb.get_page_source())
                sb.save_screenshot(str(output / 'failure-page.png'))
            except Exception:
                pass  # Preserve the original failure if browser capture is unavailable.
        log('stopped', error=str(error), error_type=type(error).__name__, current_work=current_work)
        metadata(db, 'status', 'interrupted_or_failed')
        raise
    finally:
        retention.export(catalog, output)
        catalog.close()
        metadata(db, 'active_seconds', metadata(db, 'active_seconds') + time.monotonic() - started)
        metadata(db, 'session_open', False)
        db.close()
        if sb:
            sb.quit()
        lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/stores.json')
    parser.add_argument('--categories', default='config/categories.csv')
    parser.add_argument('--store', default='100')
    parser.add_argument('--output', default='data')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--sample', type=int, default=0, metavar='CANDIDATES_PER_CATEGORY')
    run(parser.parse_args())
