"""Build a privacy-safe offline ledger for failed and unfinished coverage pages."""
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from storage import atomic_json


DATABASE = Path('data/full-coverage-20261026/queue.sqlite')
OUTPUT = Path('evidence/coverage-failure-ledger-20261030')


def classify(reason):
    if reason == 'Response category ancestry differs from required root':
        return 'response_confirmed_exclusion'
    if reason == 'Neither verified product listing nor child navigation; not legitimate empty category':
        return 'unresolved_page_type'
    return 'retryable_failure'


def reason_name(reason):
    names = {
        'Empty page title; page may still be loading': 'empty_title_or_loading',
        'Response category identifier mismatch or missing': 'category_identifier_missing_or_mismatched',
        'Location mismatch in store banner': 'store_banner_mismatch',
        'Neither verified product listing nor child navigation; not legitimate empty category': 'page_type_unresolved',
        'Response category ancestry differs from required root': 'outside_required_response_ancestry',
        'Diagnostic disk reserve below 8 GiB': 'storage_guard',
        '[Errno 92] Illegal byte sequence': 'browser_encoding_error',
        'Location mismatch: primary listing store/Pickup context missing': 'listing_store_pickup_missing',
        'Location mismatch in primary listing store context': 'listing_store_mismatch',
        'Evidence capture failed; run stopped': 'evidence_capture_failed',
        'Bounded coverage runtime reached': 'runtime_limit',
        'Abnormal page latency: 28.3s': 'page_latency_limit'
    }
    if reason.startswith('\nexceptionId:'):
        return 'browser_fetch_failure'
    return names.get(reason, 'unclassified_failure')


def build():
    db = sqlite3.connect(f'file:{DATABASE}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    rows = [dict(row) for row in db.execute(
        "SELECT category,key,url,status,reason FROM pages ORDER BY category,key")]
    db.close()
    counts = Counter(row['status'] for row in rows)
    failed = []
    for row in rows:
        if row['status'] != 'failed':
            continue
        failed.append({k: row[k] for k in ['category', 'key', 'url', 'status']} | {
            'reason': reason_name(row['reason']),
            'classification': classify(row['reason'])
        })
    unresolved = [row for row in rows if row['status'] == 'navigation_scope_unverified']
    pending = Counter(row['category'] for row in rows if row['status'] == 'pending')
    reason_counts = defaultdict(Counter)
    for row in failed:
        reason_counts[row['classification']][row['reason']] += 1
    summary = {
        'mode': 'Offline classification of the saved coverage queue; no retailer requests',
        'queue_counts': dict(counts),
        'failed_classification_counts': dict(Counter(row['classification'] for row in failed)),
        'failed_reason_counts': {name: dict(values) for name, values in reason_counts.items()},
        'pending_by_category': dict(pending),
        'navigation_scope_unverified': len(unresolved),
        'full_coverage_complete': False,
        'publication_allowed': False,
        'rules': {
            'retryable_failure': 'The page remains required and must be tried again or resolved by approved transport evidence.',
            'response_confirmed_exclusion': 'The response identified category ancestry outside the requested required root.',
            'unresolved_page_type': 'The response did not prove a listing, child navigation, or a legitimate empty category.'
        },
        'limits': [
            'Blocked, loading or empty-title pages are not counted as empty categories.',
            'Pending pages have not been reviewed and remain open.',
            'This ledger classifies saved evidence; it does not complete coverage.'
        ]
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUTPUT / 'SUMMARY.json', summary)
    atomic_json(OUTPUT / 'FAILED_PAGES.json', failed)
    atomic_json(OUTPUT / 'NAVIGATION_UNRESOLVED.json', unresolved)
    print(json.dumps(summary))


if __name__ == '__main__':
    build()
