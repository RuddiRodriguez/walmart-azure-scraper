"""One bounded live SIGKILL/resume check; raw evidence stays under data/."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import psutil
from storage import atomic_json


def run(root, plan):
    root.mkdir(parents=True, exist_ok=False)
    output = root / 'collection'
    command = [sys.executable, 'controlled_collection.py', '--plan', str(plan), '--output', str(output)]
    started = time.monotonic()
    budget = json.loads(plan.read_text())['limits']['seconds']
    result = dict(scope='One category, three products; current collector live hard interruption/resume only',
                  command=command, interruption='SIGKILL during product request after one saved accepted record', checks={})
    with (root / 'process.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        interrupted = False
        while process.poll() is None and time.monotonic() - started < budget:
            checkpoint = output / 'checkpoint.json'
            events = output / 'events.jsonl'
            if checkpoint.exists() and events.exists():
                saved = json.loads(checkpoint.read_text())
                lines = events.read_text().splitlines()
                event = json.loads(lines[-1]) if lines else {}
                if len(saved['accepted']) >= 1 and event.get('event') == 'product_started':
                    children = psutil.Process(process.pid).children(recursive=True)
                    process.kill()
                    process.wait()
                    for child in children:
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
                    interrupted = True
                    break
            time.sleep(0.05)
        if not interrupted:
            if process.poll() is None:
                for child in psutil.Process(process.pid).children(recursive=True):
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                process.kill()
                process.wait()
            result.update(passed=False, error='No qualifying interruption within original budget')
            atomic_json(root / 'recovery-result.json', result)
            return
        before = json.loads(checkpoint.read_text())
        atomic_json(root / 'interrupted-checkpoint.json', before)
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (output / 'captures').glob('*.body')}
        result['interrupted_product'] = event['product_id']
        result['saved_ids'] = list(before['accepted'])
        result['before_counts'] = before['report']['counts']
        # An incompatible plan must fail before starting a new browser/request.
        changed = json.loads(plan.read_text())
        changed['target'] += 1
        altered = root / 'altered-plan.json'
        atomic_json(altered, changed)
        invalid = subprocess.run(command[:3] + [str(altered)] + command[4:] + ['--resume'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
        result['checks']['changed_settings_rejected'] = invalid.returncode != 0 and 'Code or settings changed' in invalid.stdout
        (root / 'changed-settings.log').write_text(invalid.stdout)
        remaining = max(1, budget - (time.monotonic() - started))
        resumed = subprocess.Popen(command + ['--resume'], stdout=log, stderr=subprocess.STDOUT)
        try:
            resumed.wait(timeout=remaining + 15)
        except subprocess.TimeoutExpired:
            for child in psutil.Process(resumed.pid).children(recursive=True):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            resumed.kill()
            resumed.wait()
        after = json.loads((output / 'checkpoint.json').read_text())
        report = after['report']
        events = [json.loads(line) for line in (output / 'events.jsonl').read_text().splitlines()]
        commits = [e['product_id'] for e in events if e['event'] == 'product_committed']
        starts = [e['product_id'] for e in events if e['event'] == 'product_started']
        checks = result['checks']
        checks['original_records_unchanged'] = all(after['accepted'].get(k) == v for k, v in before['accepted'].items())
        checks['completed_target'] = bool(report['completed_attempt'] and report['target_reached'] and len(after['accepted']) == 3)
        checks['no_duplicate_commits'] = len(commits) == len(set(commits))
        checks['committed_records_not_refetched'] = all(starts.count(k) == 1 for k in before['accepted'])
        checks['interrupted_product_retried_once'] = starts.count(event['product_id']) == 2 and commits.count(event['product_id']) == 1
        checks['original_evidence_unchanged'] = all((output / 'captures' / name).exists() and hashlib.sha256((output / 'captures' / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
        checks['cumulative_counters'] = all(report['counts'][k] >= before['report']['counts'][k] for k in ['sequence', 'product_requests', 'listing_requests', 'body_bytes'])
        checks['source_count_matches'] = after['source_count'] == len(after['accepted'])
        checks['fresh_resume_control_passed'] = report.get('resume_control_passed') is True
        result.update(passed=all(checks.values()), after_counts=report['counts'], seconds=round(time.monotonic() - started, 3),
                      accepted_records=len(after['accepted']), error=report.get('error'), source_commit=report['source_commit'])
        atomic_json(root / 'recovery-result.json', result)
        print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if not args.output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Recovery output must stay in ignored data/')
    run(args.output, args.plan)
