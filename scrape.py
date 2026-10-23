"""Run a store crawl. --sample is evidence-only; it never replaces production output."""
import argparse
import csv
from collections import Counter
import fcntl
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from browser import open_browser, select_store, navigate, verify_banner, fetch_product, canary_check
from extract import discover, listing_candidates, next_data, product_record
from storage import connect, metadata, atomic_json, add_pages, save_page, save_product, records
from validate import validate


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
    code = '' if args.sample else ''.join((Path(__file__).parent / name).read_text() for name in ['scrape.py', 'browser.py', 'extract.py', 'storage.py', 'validate.py'])
    signature = hashlib.sha256((Path(args.config).read_text() + Path(args.categories).read_text() + str(args.sample) + code).encode()).hexdigest()
    if args.resume and metadata(db, 'signature') != signature:
        raise ValueError('Configuration or full-run code changed; start a fresh run')
    if args.resume and time.time() - metadata(db, 'started') > settings['max_checkpoint_age_hours'] * 3600:
        raise ValueError('Checkpoint too old; start a fresh run to avoid stale prices')
    if not args.resume:
        metadata(db, 'signature', signature)
        metadata(db, 'started', time.time())
        metadata(db, 'active_seconds', 0)
        with db:
            for category, config in categories.items():
                add_pages(db, category, [config['URL']])
    started = time.monotonic()
    def log(event, **values):
        message = {'time': datetime.now(timezone.utc).isoformat(), 'event': event, 'store': args.store, **values}
        with (output / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(message) + '\n')
        print(json.dumps(message), flush=True)
    sb = None
    try:
        sb = open_browser()
        logo = select_store(sb, store, settings, log, output)
        canary_check(sb, store, settings)
        page_count = db.execute("SELECT count(*) FROM pages WHERE status='done'").fetchone()[0]
        # Breadth-first across categories. Sample obtains a minimum from each category.
        while True:
            order = "CASE WHEN url LIKE '%/browse/%' THEN 0 ELSE 1 END,rowid" if args.sample else 'rowid'
            pending = db.execute("SELECT category,url FROM pages WHERE status='pending' ORDER BY " + order).fetchall()
            if not pending:
                break
            progressed = False
            for category, url in pending:
                if args.sample:
                    category_candidates = db.execute("SELECT count(*) FROM candidates WHERE json_extract(data, '$.category')=?", (category,)).fetchone()[0]
                    if category_candidates >= args.sample:
                        continue
                if page_count >= settings['max_pages']:
                    raise ValueError('Page safety limit reached; coverage incomplete')
                soup = navigate(sb, url, settings, log)
                verify_banner(soup, store)
                # Render lazy-loaded cards before matching structured data to visible offers.
                stable = 0
                prior_cards = -1
                for _ in range(60):
                    sb.scroll_down(900)
                    sb.sleep(0.5)
                    rendered = BeautifulSoup(sb.get_page_source(), 'html.parser')
                    card_count = len(rendered.select('[data-item-id]'))
                    stable = stable + 1 if card_count == prior_cards else 0
                    prior_cards = card_count
                    if stable >= 4:
                        break
                else:
                    raise ValueError('Lazy loading did not settle; coverage incomplete')
                soup = BeautifulSoup(sb.get_page_source(), 'html.parser')
                verify_banner(soup, store)
                source = hashlib.sha256(url.encode()).hexdigest()[:20] + '.html'
                (output / 'sources' / source).write_text(str(soup))
                candidates, rejected, search = listing_candidates(soup, category, store)
                if not args.sample and any(r['reason'] == 'not_rendered' for r in rejected):
                    raise ValueError('Local product cards missing after lazy loading; coverage incomplete')
                for candidate in candidates:
                    candidate['source'] = source
                exclusions = ['recipes', r'shop[- ]all[- ]foods?$', 'farm[- ]animals']
                links = discover(soup, categories[category]['URL'], exclusions, current_url=url)
                next_link = soup.select_one('a[aria-label="Next Page"]')
                has_next = bool(next_link and next_link.get('href'))
                if has_next:
                    next_url = urljoin(url, next_link['href'])
                    if next_url == url or db.execute("SELECT 1 FROM pages WHERE category=? AND url=? AND status='done'", (category, next_url)).fetchone():
                        raise ValueError('Pagination loop; coverage incomplete')
                    links[next_url] = 'Next Page'
                if search:
                    raw = sum(i.get('__typename') == 'Product' for stack in search.get('itemStacks', []) for i in stack.get('items', []))
                    pagination = search.get('paginationV2') or {}
                    current_page = int((pagination.get('pageProperties') or {}).get('page') or 1)
                    if raw == 0:
                        raise ValueError('Unexpected zero-product listing: ' + url)
                    if current_page < int(pagination.get('maxPage') or 1) and not has_next:
                        raise ValueError('Missing next-page control before reported final page')
                else:
                    raw = 0
                    if not links:
                        raise ValueError('Category returned neither products nor child categories: ' + url)
                save_page(db, category, url, links, candidates, rejected, raw)
                page_count += 1
                progressed = True
                log('category_page', category=category, url=url, raw=raw, local_candidates=len(candidates), discovered=len(links))
                if page_count % 20 == 0:
                    canary_check(sb, store, settings)
            if not progressed:
                break
        sample_counts = Counter(row['category'] for row in records(db))
        for key, text in db.execute("SELECT id,data FROM candidates WHERE status='pending' ORDER BY rowid").fetchall():
            candidate = json.loads(text)
            if args.sample and sample_counts[candidate['category']] >= args.sample:
                continue
            soup = fetch_product(sb, candidate['url'], settings)
            row, reason, product = product_record(candidate, soup, store, settings['private_labels'], logo)
            atomic_json(output / 'sources' / (key + '.json'), {'candidate': candidate, 'product': product, 'specifications': (next_data(soup).get('data', {}).get('idml') or {}).get('specifications'), 'reason': reason})
            save_product(db, candidate, row, reason)
            if row:
                sample_counts[candidate['category']] += 1
            log('product', id=key, accepted=bool(row), reason=reason)
            time.sleep(settings['delay_seconds'])
        canary_check(sb, store, settings)
        rows = records(db)
        pending_pages = db.execute("SELECT count(*) FROM pages WHERE status!='done'").fetchone()[0]
        pending_products = db.execute("SELECT count(*) FROM candidates WHERE status!='done'").fetchone()[0]
        review = db.execute("SELECT count(*) FROM candidates WHERE reason='promotion_review_required'").fetchone()[0]
        previous = None
        if (base / 'latest.json').exists():
            pointer = json.loads((base / 'latest.json').read_text())
            previous = json.loads((base / pointer['report']).read_text())
        report = validate(rows, list(categories), store, settings, pending_pages, pending_products, review, previous)
        if args.sample:
            sample_settings = {**settings, 'minimum_records': args.sample * len(categories), 'minimum_category_records': args.sample}
            report['sample_validation'] = validate(rows, list(categories), store, sample_settings, 0, 0, 0)
        report.update(mode='sample' if args.sample else 'full', store=store,
                      active_seconds=round(metadata(db, 'active_seconds') + time.monotonic() - started, 2),
                      elapsed_seconds=round(time.time() - metadata(db, 'started'), 2),
                      pages_processed=page_count,
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
        if not args.sample and not report['passed']:
            raise RuntimeError('Full run failed publication checks; see report.json')
    except BaseException as error:
        if sb:
            try:
                (output / 'failure-page.html').write_text(sb.get_page_source())
                sb.save_screenshot(str(output / 'failure-page.png'))
            except Exception:
                pass  # Preserve the original failure if browser capture is unavailable.
        log('stopped', error=str(error), error_type=type(error).__name__)
        metadata(db, 'status', 'interrupted_or_failed')
        raise
    finally:
        metadata(db, 'active_seconds', metadata(db, 'active_seconds') + time.monotonic() - started)
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
