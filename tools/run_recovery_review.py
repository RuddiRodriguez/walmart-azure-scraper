"""One bounded live SIGKILL/resume review of the current production collector."""
import csv
import hashlib
import json
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


def review(output, sample=3, kill_after=1, timeout=900, max_attempts=9, all_categories=False):
    output = Path(output).resolve()
    if not output.is_relative_to(Path('data').resolve()):
        raise ValueError('Recovery output must stay under ignored data/')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    started = time.monotonic()
    deadline = started + timeout
    settings = json.loads(Path('config/stores.json').read_text())
    settings.update(retries=1, max_page_seconds=45, trace_store_context=False)
    (output / 'settings.json').write_text(json.dumps(settings, indent=2) + '\n')
    if all_categories:
        (output / 'categories.csv').write_bytes(Path('config/categories.csv').read_bytes())
    else:
        with Path('config/categories.csv').open() as source:
            reader = csv.DictReader(source)
            row = next(r for r in reader if r['Category (Auto)'] == 'Household Essentials')
            fields = reader.fieldnames
        row['URL'] = 'https://www.walmart.com/browse/household-essentials/clorox/1115193_8250903_7784444'
        row['Scope'] = 'Bounded recovery sample only; not full category coverage'
        with (output / 'categories.csv').open('w') as target:
            writer = csv.DictWriter(target, fieldnames=fields)
            writer.writeheader()
            writer.writerow(row)
    command = [sys.executable, '-u', 'scrape.py', '--config', str(output / 'settings.json'),
               '--categories', str(output / 'categories.csv'), '--sample', str(sample), '--output', str(output / 'collection')]
    result = {'mode': f'one live recovery attempt, sample={sample}, all_categories={all_categories}',
              'limits': {'seconds': timeout, 'product_attempts': max_attempts, 'kill_after_products': kill_after},
              'started_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'core_sha256': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                              for name in ['scrape.py', 'browser.py', 'extract.py', 'storage.py', 'validate.py']},
              'sigkill_performed': False, 'resume_executed': False, 'recovery_passed': False}

    def save():
        result['seconds'] = round(time.monotonic() - started, 3)
        (output / 'review.json').write_text(json.dumps(result, indent=2) + '\n')

    def stop(process):
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                children = psutil.Process(process.pid).children(recursive=True)
                process.kill()
                for child in children:
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                process.wait()

    def exhausted(run):
        path = run / 'events.jsonl'
        events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        attempts = sum(e['event'] == 'product_started' for e in events)
        result['target_attempts'] = attempts
        return time.monotonic() >= deadline or attempts >= max_attempts

    worker = None
    stopper = None
    try:
        with (output / 'initial.log').open('w') as log:
            worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            pointer = output / 'collection/100/active-sample.json'
            while not pointer.exists() and worker.poll() is None and time.monotonic() < deadline:
                time.sleep(0.2)
            if not pointer.exists():
                raise RuntimeError('Recovery checkpoint not created')
            run = pointer.parent / 'runs' / json.loads(pointer.read_text())['run_id']
            result['run'] = str(run.relative_to(output))
            with (output / 'hard-stop.log').open('w') as evidence:
                stopper = subprocess.Popen([sys.executable, '-m', 'tools.hard_stop_review', str(worker.pid), str(run),
                                            '--event', 'product_started', '--minimum-products', str(kill_after),
                                            '--timeout', str(min(timeout, 3600))],
                                           stdout=evidence, stderr=subprocess.STDOUT)
                while stopper.poll() is None:
                    if exhausted(run):
                        raise RuntimeError('Recovery request/runtime budget reached')
                    time.sleep(0.2)
                result['stopper_exit'] = stopper.wait()
            worker.wait(timeout=30)
            result['initial_exit'] = worker.returncode
            result['sigkill_performed'] = (run / 'hard-stop.json').exists() and worker.returncode == -signal.SIGKILL
            save()
            if not result['sigkill_performed']:
                raise RuntimeError('Planned live SIGKILL did not occur; no recovery claim')
        if time.monotonic() >= deadline:
            raise RuntimeError('No time remains for resume')
        with (output / 'resume.log').open('w') as log:
            worker = subprocess.Popen(command + ['--resume'], stdout=log, stderr=subprocess.STDOUT)
            result['resume_executed'] = True
            save()
            while worker.poll() is None:
                if exhausted(run):
                    raise RuntimeError('Recovery request/runtime budget reached')
                time.sleep(0.2)
            result['resume_exit'] = worker.returncode
        if worker.returncode == 0:
            with (output / 'verification.log').open('w') as log:
                checked = subprocess.run([sys.executable, '-m', 'tools.verify_hard_recovery', str(run)], stdout=log, stderr=subprocess.STDOUT)
            result['recovery_passed'] = checked.returncode == 0
    except Exception as error:
        result['error'] = str(error)
    finally:
        if stopper and stopper.poll() is None:
            stopper.terminate()
            stopper.wait()
        if worker:
            stop(worker)
        save()
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--sample', type=int, default=3)
    parser.add_argument('--kill-after', type=int, default=1)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--max-attempts', type=int, default=9)
    parser.add_argument('--all-categories', action='store_true')
    args = parser.parse_args()
    if not review(args.output, args.sample, args.kill_after, args.timeout,
                  args.max_attempts, args.all_categories)['recovery_passed']:
        raise SystemExit(1)
