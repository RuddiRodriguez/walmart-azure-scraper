"""SIGKILL one explicitly selected review runner after its next page-load event."""
import argparse
import json
import os
import signal
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pid', type=int)
    parser.add_argument('run', type=Path)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--event', choices=['page_loaded', 'product_started'], default='page_loaded')
    parser.add_argument('--minimum-products', type=int, default=0)
    args = parser.parse_args()
    process = psutil.Process(args.pid)
    if 'scrape.py' not in process.cmdline():
        raise SystemExit('Selected process is not scrape.py')
    events_path = args.run / 'events.jsonl'
    before_lines = len(events_path.read_text().splitlines())
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        new_pages = [e for e in events[before_lines:] if e['event'] == args.event]
        completed_products = sum(e['event'] == 'product' and e.get('accepted') for e in events)
        if new_pages and completed_products >= args.minimum_products:
            children = process.children(recursive=True)
            os.kill(args.pid, signal.SIGKILL)
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            db = sqlite3.connect(args.run / 'checkpoint.sqlite')
            result = {
                'time_utc': datetime.now(timezone.utc).isoformat(),
                'signal': 'SIGKILL', 'last_event': new_pages[-1],
                'completed_pages': list(db.execute("SELECT category,url FROM pages WHERE status='done'")),
                'committed_ids': [r[0] for r in db.execute('SELECT id FROM records')],
                'sqlite_integrity': db.execute('PRAGMA integrity_check').fetchone()[0],
                'scope': 'live process killed after ' + args.event + '; browser children also terminated; committed state recorded below',
            }
            db.close()
            (args.run / 'hard-stop.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps({'signal': 'SIGKILL', 'completed_pages': len(result['completed_pages']), 'sqlite_integrity': result['sqlite_integrity']}))
            break
        if not process.is_running():
            raise SystemExit('Runner exited before interruption')
        time.sleep(0.05)
    else:
        raise SystemExit('No new page-load event; no interruption performed')
