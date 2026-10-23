"""Check captured SIGKILL state against later live progress in the same run."""
import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path


def verify(run):
    before = json.loads((run / 'hard-stop.json').read_text())
    events = [json.loads(line) for line in (run / 'events.jsonl').read_text().splitlines()]
    pages = Counter((e['category'], e['url']) for e in events if e['event'] == 'category_page')
    completions = Counter(e['id'] for e in events if e['event'] == 'product')
    db = sqlite3.connect(run / 'checkpoint.sqlite')
    ids = {r[0] for r in db.execute('SELECT id FROM records')}
    last = before['last_event']
    checks = {
        'sqlite_integrity': db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok',
        'prior_pages_completed_once': all(pages[tuple(page)] == 1 for page in before['completed_pages']),
        'prior_records_retained': set(before['committed_ids']) <= ids,
        'prior_products_completed_once': all(completions[key] == 1 for key in before['committed_ids']),
        'interrupted_product_was_uncommitted': last['id'] not in before['committed_ids'],
        'interrupted_product_attempted_twice': sum(e['event'] == 'product_started' and e['id'] == last['id'] for e in events) == 2,
        'interrupted_product_completed_once': completions[last['id']] == 1,
    }
    db.close()
    result = {'mode': 'live SIGKILL after product request start, followed by identical-code resume',
              'passed': all(checks.values()), 'checks': checks, 'committed_records_before_kill': len(before['committed_ids']),
              'interrupted_product': last['id'], 'limit': 'Recovery proof only, not full catalog completion; precise network packet timing is not measured.'}
    (run / 'hard-recovery.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    verify(parser.parse_args().run)
