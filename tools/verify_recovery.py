"""Audit an intentional live interruption after its resumed run finishes."""
import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    before = json.loads((args.run / 'interruption-before.json').read_text())
    report = json.loads((args.run / 'report.json').read_text())
    events = [json.loads(line) for line in (args.run / 'events.jsonl').read_text().splitlines()]
    db = sqlite3.connect(f'file:{args.run / "checkpoint.sqlite"}?mode=ro', uri=True)
    ids = [r[0] for r in db.execute('SELECT id FROM records')]
    db.close()
    product_events = Counter(e['id'] for e in events if e['event'] == 'product')
    page_events = Counter((e['category'], e['url']) for e in events if e['event'] == 'category_page')
    checks = {
        'previous_products_preserved': set(before['committed_ids_before']) <= set(ids),
        'previous_products_processed_once': all(product_events[key] == 1 for key in before['committed_ids_before']),
        'previous_pages_processed_once': all(page_events[tuple(page)] == 1 for page in before['completed_pages_before']),
        'no_duplicate_ids': len(ids) == len(set(ids)),
        'sample_validation_passed': report['sample_validation']['passed'],
        'intentional_interrupt_recorded': any(e.get('error_type') == 'KeyboardInterrupt' for e in events),
    }
    result = {**before, 'checks': checks, 'passed': all(checks.values()), 'final_records': len(ids),
              'scope': 'live local sample, interruption between product requests after three commits; not a mid-response hard kill or Azure test'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'final_records': len(ids), 'checks': checks}))
    if not result['passed']:
        raise SystemExit(1)
