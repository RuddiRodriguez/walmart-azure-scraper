"""Interrupt an explicitly selected local review process after three committed products."""
import argparse
import json
import os
import signal
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pid', type=int)
    parser.add_argument('run', type=Path)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        os.kill(args.pid, 0)
        db = sqlite3.connect(f'file:{args.run / "checkpoint.sqlite"}?mode=ro', uri=True)
        ids = [r[0] for r in db.execute('SELECT id FROM records ORDER BY id')]
        pages = list(db.execute("SELECT category,url FROM pages WHERE status='done' ORDER BY category,url"))
        db.close()
        if len(ids) >= 3:
            evidence = {'time_utc': datetime.now(timezone.utc).isoformat(),
                        'mode': 'intentional interruption during live product collection',
                        'committed_ids_before': ids, 'completed_pages_before': pages}
            (args.run / 'interruption-before.json').write_text(json.dumps(evidence, indent=2) + '\n')
            os.kill(args.pid, signal.SIGINT)
            print(json.dumps({'interrupted_pid': args.pid, 'committed_records': len(ids)}), flush=True)
            break
        time.sleep(1)
    else:
        raise SystemExit('Timed out without interrupting; no recovery claim')
