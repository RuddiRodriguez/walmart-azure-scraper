"""Record real local command output as a terminal walkthrough; never runs a live scrape."""
import argparse
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def record(destination):
    destination.mkdir(parents=True, exist_ok=True)
    commands = [
        [sys.executable, '-c', "import json,csv; s=json.load(open('config/stores.json')); print('LOCAL REVIEW WALKTHROUGH - no Azure or contest submission'); print('Trial store:',s['stores'][0]['id'],s['stores'][0]['name']); print('Required parent categories:',len(list(csv.DictReader(open('config/categories.csv')))))"],
        [sys.executable, 'check_requirements.py'],
        [sys.executable, 'check_storage_recovery.py'],
        [sys.executable, '-c', "import json; p=json.load(open('evidence/products-500.json')); print('Historical genuine demonstration:',len(p),'records'); print('Historical collection dates:',min(r['crawl_date'] for r in p),'to',max(r['crawl_date'] for r in p)); print('This is not a fresh full-catalog run.'); print(open('docs/CURRENT_RESULTS.txt').read())"],
        [sys.executable, '-c', "import json; r=json.load(open('evidence/hard-product-recovery/hard-recovery.json')); print(json.dumps(r,indent=2))"],
        [sys.executable, '-c', "print('RUNNING INSTRUCTIONS (shown, not executed here)'); print('python scrape.py --store 100 --sample 3'); print('python scrape.py --store 100'); print('python scrape.py --store 100 --resume'); print('Inspect report.json and events.jsonl. Only a passing full run updates latest.json.'); print('See docs/REVIEW_STATUS.md for unresolved requirements. Azure testing remains last.')"],
    ]
    started = time.monotonic()
    events = []
    transcript = []
    def emit(text):
        events.append([round(time.monotonic() - started, 3), 'o', text.replace('\n', '\r\n')])
        transcript.append(text)
    emit('Recorded at ' + datetime.now(timezone.utc).isoformat() + '\n')
    for command in commands:
        emit('\n$ ' + shlex.join(['python'] + command[1:]) + '\n')
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # Preserve every actual output line and space it for readable playback.
        for line in result.stdout.splitlines():
            emit(line + '\n')
            time.sleep(0.1)
        emit('[exit code ' + str(result.returncode) + ']\n')
        if result.returncode:
            raise RuntimeError('Walkthrough command failed')
        time.sleep(4)
    header = {'version': 2, 'width': 120, 'height': 30, 'timestamp': int(time.time()),
              'title': 'Recorded local Walmart scraper review; offline checks and captured live evidence',
              'env': {'TERM': 'xterm-256color', 'SHELL': '/bin/sh'}}
    (destination / 'walkthrough.cast').write_text('\n'.join(json.dumps(x) for x in [header] + events) + '\n')
    (destination / 'transcript.txt').write_text(''.join(transcript))
    print('Recorded', len(events), 'terminal output events; duration', round(time.monotonic()-started, 1), 'seconds')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    record(parser.parse_args().destination)
