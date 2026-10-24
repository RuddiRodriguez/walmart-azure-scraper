"""Bounded final live checks, then stop. No publication or client communication."""
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

python = sys.executable
session = Path('data/final-session-20261024')
results = []

def run(name, command, seconds=300):
    with (session / (name + '.log')).open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            process.send_signal(signal.SIGINT)
            code = process.wait(timeout=30)
    results.append({'stage': name, 'returncode': code})
    (session / 'final-checks-status.json').write_text(json.dumps(results, indent=2) + '\n')
    return code

output = session / 'recovery-current'
command = [python, '-u', 'scrape.py', '--config', str(session / 'trace-config.json'), '--sample', '1', '--output', str(output)]
with (session / 'recovery-initial.log').open('w') as log:
    collector = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    pointer = output / '100/active-sample.json'
    deadline = time.monotonic() + 30
    while not pointer.exists() and collector.poll() is None and time.monotonic() < deadline:
        time.sleep(0.5)
    if not pointer.exists():
        collector.send_signal(signal.SIGINT)
        collector.wait(timeout=30)
        raise SystemExit('Recovery checkpoint was not created')
    checkpoint = output / '100/runs' / json.loads(pointer.read_text())['run_id']
    code = run('hard-stop', [python, 'hard_stop_review.py', str(collector.pid), str(checkpoint), '--event', 'product_started', '--minimum-products', '1'], 200)
    if code != 0:
        if collector.poll() is None:
            collector.send_signal(signal.SIGINT)
        collector.wait(timeout=30)
    else:
        collector.wait(timeout=30)
        if run('recovery-resume', command + ['--resume'], 600) == 0:
            run('hard-recovery-verify', [python, 'verify_hard_recovery.py', str(checkpoint)], 30)
    destination = Path('evidence/final-session-20261024/recovery-current')
    if run('recovery-export', [python, 'export_run_evidence.py', str(checkpoint), str(destination)], 30) == 0:
        run('recovery-source-audit', [python, 'audit_run.py', str(destination)], 30)
    for name in ['hard-stop.json', 'hard-recovery.json']:
        if (checkpoint / name).exists():
            (destination / name).write_bytes((checkpoint / name).read_bytes())

spot = session / 'price-spot-check'
run('price-spot-check', [python, 'spot_check.py', 'evidence/products-500.json', str(spot)], 300)
safe = Path('evidence/final-session-20261024/price-spot-check')
safe.mkdir(parents=True, exist_ok=True)
for name in ['checks.json', 'events.jsonl', 'selected-store.json']:
    if (spot / name).exists():
        (safe / name).write_bytes((spot / name).read_bytes())
Path('evidence/final-session-20261024/final-checks-status.json').write_text(json.dumps(results, indent=2) + '\n')
with Path('WORK_LOG.md').open('a') as log:
    log.write('\nBounded final checks results: ' + json.dumps(results) + '\n')
