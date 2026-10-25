"""Offline audit/export of one controlled run. Original response bodies stay private."""
import argparse
from collections import Counter
import hashlib
import json
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup
from capture_store_drift import listing_from_rendered
from extract import next_data, product_record
from scrape import verify_listing_store
from storage import atomic_json
from trace_store_context import product_context
from validate import validate


def audit(run, evidence):
    run, evidence = Path(run), Path(evidence)
    report = json.loads((run / 'report.json').read_text())
    rows = json.loads((run / 'products.json').read_text())
    sources = json.loads((run / 'source-records.json').read_text())
    settings = json.loads(Path('config/stores.json').read_text())
    store = settings['stores'][0]
    errors, metadata, contexts, indexed = [], [], [], {}
    for name, digest in report['source_hashes'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            committed = subprocess.check_output(['git', 'show', report['source_commit'] + ':' + name])
            if hashlib.sha256(committed).hexdigest() != digest:
                errors.append('Recorded source version/hash mismatch: ' + name)
    for path in sorted((run / 'captures').glob('*.json')):
        item = json.loads(path.read_text())
        if 'body_file' in item:
            body = (path.parent / item['body_file']).read_bytes()
            if hashlib.sha256(body).hexdigest() != item['body_sha256'] or len(body) != item['body_bytes']:
                errors.append('Original body hash/length mismatch: ' + item['id'])
            indexed[item['sequence']] = item
        safe = {k: item[k] for k in ['id', 'session', 'kind', 'sequence', 'request', 'response', 'body_bytes', 'body_sha256', 'body_scope'] if k in item}
        if 'error' in item:
            safe['error_type'] = item['error'].get('error_type')
        metadata.append(safe)
    derived, snapshots = {}, 0
    for entry in report['pages']:
        if 'snapshot' not in entry:
            continue
        native = run / entry['snapshot']
        if hashlib.sha256(native.read_bytes()).hexdigest() != entry['snapshot_sha256']:
            errors.append('Native snapshot hash mismatch: ' + entry['snapshot'])
        snapshots += 1
        sequence = entry.get('listing_sequence')
        if sequence not in indexed:
            continue
        item = indexed[sequence]
        page = BeautifulSoup((run / 'captures' / item['body_file']).read_bytes(), 'html.parser')
        search = next_data(page).get('searchResult')
        if search:
            verify_listing_store(search, store)
            found, _, _ = listing_from_rendered(native, page, entry['category'], store)
            for candidate in found:
                derived[(sequence, candidate['item_id'])] = candidate
        page.decompose()
    row_map = {r['url']: r for r in rows}
    verified_sources = []
    for source in sources:
        sequence = source['product_sequence']
        item = indexed[sequence]
        page = BeautifulSoup((run / 'captures' / item['body_file']).read_bytes(), 'html.parser')
        product = next_data(page)['data']['product']
        candidate = source['candidate']
        row = row_map[candidate['url']]
        context = product_context(product, store)
        identity = str(product.get('usItemId')) == candidate['item_id']
        native_match = derived.get((source['listing_sequence'], candidate['item_id'])) == candidate
        parsed, reason, _ = product_record(candidate, page, store, settings['private_labels'], row['store_logo'])
        fields_match = bool(parsed) and all(parsed[k] == row[k] for k in row if k != 'crawl_date')
        passed = context['store_matches'] and identity and native_match and fields_match and reason == source['reason'] and product == source['product']
        if not passed:
            errors.append('Accepted-record source replay mismatch: ' + candidate['item_id'])
        verified_sources.append(dict(product_id=candidate['item_id'], product_sequence=sequence,
                                     listing_sequence=source['listing_sequence'], category=candidate['category'],
                                     body_sha256=item['body_sha256'], listing_price_text=candidate['price_text'],
                                     current_price_info=product.get('priceInfo'), acceptance_reason=reason,
                                     source_replay_passed=passed, **{k: context[k] for k in ['store_id', 'zip', 'intent']}))
        page.decompose()
    for sequence, item in indexed.items():
        if item['kind'] != 'product':
            continue
        page = BeautifulSoup((run / 'captures' / item['body_file']).read_bytes(), 'html.parser')
        try:
            product = next_data(page).get('data', {}).get('product') or {}
            contexts.append(dict(sequence=sequence, **product_context(product, store)))
        except (ValueError, KeyError, TypeError):
            contexts.append(dict(sequence=sequence, structured_context_unavailable=True,
                                 response_status=item.get('response', {}).get('status')))
        page.decompose()
    names = [c['category'] for c in report['plan']['categories']]
    unavailable = {s['candidate']['url'] for s in sources if s['reason'] == 'retained_unavailable'}
    checked = validate(rows, names, store, {**settings, 'minimum_records': report['plan']['target'],
                       'minimum_category_records': report['plan']['minimum_per_category']}, 0, 0, 0,
                       unavailable_urls=unavailable)
    if len(rows) != len(sources):
        errors.append('Accepted record/source count mismatch')
    result = dict(mode='Offline audit of this fresh controlled live run; not uncapped coverage',
                  source_commit=report['source_commit'], source_hashes=report['source_hashes'],
                  started_utc=report['started_utc'], seconds=report['seconds'], counts=report['counts'],
                  accepted_records=len(rows), category_counts=report['category_counts'],
                  page_successes=sum(p['status'] == 'reviewed' for p in report['pages']),
                  page_failures=sum(p['status'] == 'failed' for p in report['pages']),
                  rejected_product_reasons=dict(Counter(o.get('acceptance_reason') for o in report['observations']
                      if o.get('acceptance_reason') not in [None, '', 'retained_unavailable'])),
                  request_error_types=dict(Counter(m.get('error_type') for m in metadata if m.get('error_type'))),
                  wrong_store_observations=sum(not o['store_matches'] for o in report['observations'] if not o['diagnostic_only']),
                  diagnostic_refetches=sum(o['diagnostic_only'] for o in report['observations']),
                  unavailable_successes=len(unavailable),
                  handled_failures=report.get('failures', []),
                  excluded_listing_or_product_reasons=report['exclusions'],
                  target_reached=report['target_reached'], completed_attempt=report['completed_attempt'],
                  stop_reason=report.get('error'), captured_bodies_hash_verified=len(indexed),
                  native_snapshots_hash_verified=snapshots, source_replays=len(verified_sources),
                  accepted_evidence_passed=not errors, audit_errors=errors, sample_validation=checked,
                  sample_accepted=bool(report['target_reached'] and report['completed_attempt'] and checked['passed'] and not errors),
                  pair_captured_private=report['pair_captured'], full_coverage_complete=False,
                  pending_pages=report['pending_pages'], unattempted_candidate_count=report['unattempted_candidate_count'],
                  genuine_offers_requirement='Open; this collection does not substitute for verified offer examples',
                  raw_pair_requirement='Open unless actual pair exists and privacy-reviewed evidence is prepared',
                  scope_note='Source-valid partial rows remain partial if run stopped. No historical data merged. No production pointer or client submission.')
    evidence.mkdir(parents=True, exist_ok=True)
    for name, value in [('summary.json', result), ('products.json', rows), ('capture-metadata.json', metadata),
                        ('source-contexts.json', contexts), ('accepted-source-audit.json', verified_sources),
                        ('page-decisions.json', report['pages'])]:
        atomic_json(evidence / name, value)
    atomic_json(evidence / 'SHA256SUMS.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(evidence.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.json'})
    print(json.dumps({k: result[k] for k in ['accepted_records', 'category_counts', 'sample_accepted', 'accepted_evidence_passed', 'stop_reason']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    audit(args.run, args.evidence)
