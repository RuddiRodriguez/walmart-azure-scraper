"""Inventory local run checkpoints, including failed and intentionally stopped attempts."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def report():
    runs = []
    for checkpoint in sorted(Path('data').rglob('checkpoint.sqlite')):
        folder = checkpoint.parent
        db = sqlite3.connect(f'file:{checkpoint}?mode=ro', uri=True)
        meta = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM meta')}
        events_path = folder / 'events.jsonl'
        events = [json.loads(line) for line in events_path.read_text().splitlines()] if events_path.exists() else []
        failure = json.loads((folder / 'failure.json').read_text()) if (folder / 'failure.json').exists() else None
        result = json.loads((folder / 'report.json').read_text()) if (folder / 'report.json').exists() else None
        rows = [json.loads(data) for data, in db.execute('SELECT data FROM records')]
        counts = {}
        for row in rows:
            counts[row['category']] = counts.get(row['category'], 0) + 1
        runs.append({'path': str(folder), 'started_utc': datetime.fromtimestamp(meta['started'], timezone.utc).isoformat(),
                     'status': meta.get('status', 'unfinished'), 'session_open': meta.get('session_open'),
                     'signature': meta.get('signature'), 'records': len(rows), 'category_counts': counts,
                     'page_states': dict(db.execute('SELECT status,count(*) FROM pages GROUP BY status')),
                     'candidate_states': [{'status': status, 'reason': reason, 'count': count} for status, reason, count in db.execute('SELECT status,reason,count(*) FROM candidates GROUP BY status,reason')],
                     'last_event': events[-1] if events else None, 'failure': failure,
                     'sample_passed': result.get('sample_validation', {}).get('passed') if result else None,
                     'full_passed': result.get('passed') if result else None,
                     'active_seconds': result.get('active_seconds') if result else meta.get('active_seconds'),
                     'active_time_complete': not meta.get('active_time_incomplete', False),
                     'hard_stop_evidence': [p.name for p in folder.glob('hard-*.json')]})
        db.close()
    output = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'runs': runs,
              'limits': 'Unfinished/session-open state does not prove a process is running. Older checkpoints predate explicit crash-time accounting. Prior failure files remain after successful resume.'}
    Path('evidence/local-run-register.json').write_text(json.dumps(output, indent=2) + '\n')
    print('Recorded', len(runs), 'local run attempts')


if __name__ == '__main__':
    report()
