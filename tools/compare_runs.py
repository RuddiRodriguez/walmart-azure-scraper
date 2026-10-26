"""Compare two exported live runs without treating changing retail offers as fabricated errors."""
import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def compare(first, second, destination):
    runs = []
    for folder in [first, second]:
        report_path = folder / 'report.json'
        rows = json.loads((folder / ('products.json' if (folder / 'products.json').exists() else 'products.partial.json')).read_text())
        if report_path.exists():
            report = json.loads(report_path.read_text())
        else:
            failure = json.loads((folder / 'failure.json').read_text())
            events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
            report = {'records': len(rows), 'mode': failure['mode'], 'active_seconds': failure.get('active_seconds'),
                      'elapsed_seconds': failure.get('elapsed_seconds'), 'active_time_complete': failure.get('active_time_complete'),
                      'elapsed_event_span_seconds': (datetime.fromisoformat(events[-1]['time']) - datetime.fromisoformat(events[0]['time'])).total_seconds(),
                      'category_counts': dict(Counter(r['category'] for r in rows)), 'passed': False,
                      'sample_validation': {'passed': False}, 'signature': events[0].get('signature'), 'failure': failure}
        products = {r['url'].split('?')[0].rstrip('/').split('/')[-1]: r for r in rows}
        runs.append((report, products))
    left, right = runs[0][1], runs[1][1]
    common = sorted(left.keys() & right.keys())
    changes = [{'id': key, 'before': {f: left[key][f] for f in ['regular_price', 'sale_price']},
                'after': {f: right[key][f] for f in ['regular_price', 'sale_price']}}
               for key in common if any(left[key][f] != right[key][f] for f in ['regular_price', 'sale_price'])]
    result = {'mode': 'comparison of separately collected live runs; calculation itself is offline',
              'runs': [{'folder': str(folder), 'records': report['records'], 'mode': report['mode'],
                        'active_seconds': report['active_seconds'], 'elapsed_seconds': report['elapsed_seconds'],
                        'active_time_complete': report.get('active_time_complete'),
                        'elapsed_event_span_seconds': report.get('elapsed_event_span_seconds'), 'failure': report.get('failure'),
                        'category_counts': report['category_counts'],
                        'sample_passed': report.get('sample_validation', {}).get('passed'),
                        'full_passed': report['passed'], 'signature': report.get('signature')}
                       for folder, (report, _) in zip([first, second], runs)],
              'common_ids': len(common), 'only_first': sorted(left.keys() - right.keys()),
              'only_second': sorted(right.keys() - left.keys()), 'price_changes': changes,
              'same_category_counts': runs[0][0]['category_counts'] == runs[1][0]['category_counts'],
              'same_code_and_configuration': bool(runs[0][0].get('signature')) and runs[0][0].get('signature') == runs[1][0].get('signature'),
              'limit': 'Short samples do not prove complete catalog reliability. Real assortment, ordering and prices may change.'}
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'common_ids': len(common), 'price_changes': len(changes), 'same_category_counts': result['same_category_counts']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path)
    parser.add_argument('second', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    compare(args.first, args.second, args.destination)
