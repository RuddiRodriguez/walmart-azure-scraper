"""Reconcile saved cross-root coverage exclusions without retailer requests."""
import json
import sqlite3
from pathlib import Path

from storage import atomic_json


DATABASE = Path('data/full-coverage-20261026/queue.sqlite')
EVIDENCE = Path('evidence/point3-coverage-queue-20261026')
OUTPUT = Path('evidence/coverage-exclusion-mapping-20261031.json')


def pages(batch):
    return json.loads((EVIDENCE / batch / 'report.json').read_text())['pages']


def page(batch, url):
    matches = [item for item in pages(batch) if item['url'] == url]
    assert len(matches) == 1, (batch, url, len(matches))
    return matches[0]


def check():
    art_url = 'https://www.walmart.com/browse/arts-crafts-sewing/transfer-papers/1334134_5899871_9677556_8181267'
    kids_beauty_url = 'https://www.walmart.com/browse/beauty/kids-baby-sunscreen/1085666_1007039_1001508_1620920'
    kids_personal_url = 'https://www.walmart.com/browse/personal-care/kids-baby-sunscreen/1005862_1001508_1620920'
    tanning_url = 'https://www.walmart.com/browse/beauty/tanning-lotions-oils/1085666_1007039_1001508_7306596'
    sunscreen_url = 'https://www.walmart.com/browse/beauty/sunscreen/1085666_1007039_1001508_8279042'
    parent_urls = [
        'https://www.walmart.com/browse/personal-care/sun-care/1005862_1001508',
        'https://www.walmart.com/browse/personal-care/sun-care/1005862_1001508?page=2',
        'https://www.walmart.com/browse/personal-care/sun-care/1005862_1001508?page=3',
        'https://www.walmart.com/browse/personal-care/sun-care/1005862_1001508?page=4',
    ]
    source_batches = {
        art_url: 'batch-00637-1793035060',
        kids_beauty_url: 'batch-00637-1793035060',
        kids_personal_url: 'batch-00637-1793035060',
        tanning_url: 'batch-01217-1793063813',
        sunscreen_url: 'batch-01217-1793063813',
        parent_urls[0]: 'batch-00957-1793041686',
        parent_urls[1]: 'batch-02777-1793197785',
        parent_urls[2]: 'batch-03577-1793216774',
        parent_urls[3]: 'batch-03996-1793258721',
    }
    saved = {url: page(batch, url) for url, batch in source_batches.items()}
    assert saved[art_url]['status'] == 'failed'
    assert saved[art_url]['response_category_id'] == '1334134_3123463_8181267'
    assert saved[kids_beauty_url]['response_category_id'] == '1005862_1001508_1620920'
    assert saved[kids_personal_url]['status'] == 'reviewed'
    assert saved[kids_personal_url]['response_category_id'] == '1005862_1001508_1620920'
    assert saved[tanning_url]['response_category_id'] == '1005862_1001508_7306596'
    assert saved[sunscreen_url]['response_category_id'] == '1005862_1001508_8279042'
    assert all(saved[url]['status'] == 'reviewed' for url in parent_urls)
    assert all(saved[url]['response_category_id'] == '1005862_1001508' for url in parent_urls)

    db = sqlite3.connect(f'file:{DATABASE}?mode=ro', uri=True)
    rows = db.execute('SELECT category,key,url,status,reason FROM pages').fetchall()
    db.close()
    by_pair = {(row[0], row[1]): row for row in rows}
    assert by_pair['Personal Care', '1620920#1'][3] == 'reviewed'
    assert all(by_pair['Personal Care', f'1001508#{number}'][3] == 'reviewed'
               for number in range(1, 5))
    assert all(by_pair[category, f'{key}#1'][3] == 'failed' for category, key in [
        ('Art Supplies', '8181267'), ('Beauty', '1620920'),
        ('Beauty', '7306596'), ('Beauty', '8279042'),
    ])
    counts = {}
    for status in ['pending', 'failed', 'navigation_scope_unverified']:
        counts[status] = sum(row[3] == status for row in rows)
    retryable = sum(row[3] == 'failed' and row[4] not in {
        'Response category ancestry differs from required root',
        'Neither verified product listing nor child navigation; not legitimate empty category',
    } for row in rows)
    unresolved_failed = sum(
        row[3] == 'failed' and
        row[4] == 'Neither verified product listing nor child navigation; not legitimate empty category'
        for row in rows)
    assert counts == {'pending': 780, 'failed': 229, 'navigation_scope_unverified': 9}
    assert retryable == 216 and unresolved_failed == 9

    mappings = [
        {
            'source_category': 'Beauty',
            'source_url': kids_beauty_url,
            'decision': 'equivalent_reviewed_leaf',
            'response_root': 'Personal Care (1005862)',
            'reviewed_location': kids_personal_url,
            'evidence': str(EVIDENCE / source_batches[kids_personal_url] / 'report.json'),
        },
        {
            'source_category': 'Beauty',
            'source_url': tanning_url,
            'decision': 'mapped_to_reviewed_parent',
            'response_root': 'Personal Care (1005862)',
            'response_leaf': 'Tanning Lotions & Oils (1005862_1001508_7306596)',
            'reviewed_location': parent_urls,
            'evidence': [str(EVIDENCE / source_batches[url] / 'report.json') for url in parent_urls],
        },
        {
            'source_category': 'Beauty',
            'source_url': sunscreen_url,
            'decision': 'mapped_to_reviewed_parent',
            'response_root': 'Personal Care (1005862)',
            'response_leaf': 'Sunscreen (1005862_1001508_8279042)',
            'reviewed_location': parent_urls,
            'evidence': [str(EVIDENCE / source_batches[url] / 'report.json') for url in parent_urls],
        },
        {
            'source_category': 'Art Supplies',
            'source_url': art_url,
            'decision': 'legitimate_exclusion_relative_to_required_root',
            'required_root': 'Art Supplies (1334134_5899871)',
            'response_root': 'Die Cutting (1334134_3123463)',
            'response_leaf': 'Transfer Papers (1334134_3123463_8181267)',
            'evidence': str(EVIDENCE / source_batches[art_url] / 'report.json'),
        },
    ]
    result = {
        'mode': 'Offline reconciliation from saved response reports and queue; no retailer requests',
        'passed': True,
        'mappings': mappings,
        'open_work_unchanged': {
            'pending': counts['pending'],
            'retryable_failures': retryable,
            'unresolved_failed_pages': unresolved_failed,
            'navigation_scope_unverified': counts['navigation_scope_unverified'],
            'unresolved_total': unresolved_failed + counts['navigation_scope_unverified'],
            'full_coverage_complete': False,
        },
        'limits': [
            'Mapping reconciles four response-ancestry exclusions only.',
            'Reviewed parent mapping does not close pending, retryable or unresolved pages.',
            'No new collection or full-coverage claim is made.',
        ],
    }
    atomic_json(OUTPUT, result)
    print(json.dumps(result))


if __name__ == '__main__':
    check()
