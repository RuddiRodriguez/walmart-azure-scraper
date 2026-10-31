"""Run the complete offline client regression and record one review result."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from storage import atomic_json


CHECKS = [
    ('safeguards', 'tools.check_review_changes', 'evidence/review-regression.json'),
    ('assortment', 'tools.check_unverified_assortment_gate',
     'evidence/unverified-assortment-gate-20261031.json'),
    ('package_sizes', 'tools.check_package_sizes', 'evidence/package-size-checks-20261030.json'),
    ('package_size_replay', 'tools.replay_package_size_changes',
     'evidence/package-size-replay-20261031.json'),
    ('historical_retention', 'tools.check_retention',
     'evidence/retention-step2-20261026/retention-checks.json'),
    ('runner_flow', 'tools.check_runner_flow', 'evidence/runner-flow-check.json'),
    ('saved_source_replay', 'tools.replay_evidence', 'evidence/replay-report.json'),
    ('taxonomy_scope', 'tools.check_taxonomy_queue', None),
    ('coverage_queue', 'tools.check_coverage_queue',
     'evidence/point3-coverage-queue-20261026/offline-checks.json'),
    ('coverage_ledger', 'tools.reconcile_coverage_exclusions',
     'evidence/coverage-exclusion-mapping-20261031.json'),
]

HISTORICAL = [
    ('latest-large-recovery-20261027', 132, 'historical bounded recovery'),
    ('latest-large-repeat-20261027', 132, 'historical bounded repeat'),
    ('controlled-skip-invalid-20261025', 506, 'historical controlled demonstration'),
    ('controlled-skip-invalid-repeat-20261025', 506, 'historical controlled repeat'),
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run():
    datasets = []
    before = {}
    for name, records, label in HISTORICAL:
        path = Path('evidence') / name / 'products.json'
        rows = json.loads(path.read_text())
        assert len(rows) == records, (name, len(rows), records)
        before[str(path)] = digest(path)
        datasets.append({
            'name': name,
            'records': records,
            'label': label,
            'historical': True,
            'clean_current_version_run': False,
            'products_sha256': before[str(path)],
        })

    results = []
    for name, module, evidence in CHECKS:
        process = subprocess.run(
            [sys.executable, '-m', module], text=True, capture_output=True)
        passed = process.returncode == 0
        if evidence:
            saved = json.loads(Path(evidence).read_text())
            passed = passed and saved.get('passed') is True
        results.append({
            'name': name,
            'command': f'{sys.executable} -m {module}',
            'exit_code': process.returncode,
            'passed': passed,
            'evidence': evidence or '',
        })

    unchanged = {path: digest(path) == value for path, value in before.items()}
    coverage = json.loads(
        Path('evidence/coverage-exclusion-mapping-20261031.json').read_text())
    package_replay = json.loads(Path('evidence/package-size-replay-20261031.json').read_text())
    result = {
        'mode': 'Full offline regression; no browser, network, Azure, proxy or live collection',
        'source_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'passed': all(item['passed'] for item in results) and all(unchanged.values()),
        'checks': results,
        'historical_datasets': datasets,
        'historical_products_unchanged': unchanged,
        'historical_132_replay': {
            name: {
                'records_replayed': value['records_replayed'],
                'changed_records': value['changed_records'],
                'changed_fields': value['changed_fields'],
            }
            for name, value in package_replay['runs'].items()
        },
        'coverage_work_remains_open': coverage['open_work_unchanged'],
        'limits': [
            'Historical 132-product and 506-product datasets are not clean current-version runs.',
            'Historical product files were hash-checked and not rewritten.',
            'Offline regression does not prove fresh retailer access or full category coverage.',
        ],
    }
    output = Path('evidence/full-offline-regression-20261031')
    output.mkdir(exist_ok=True)
    atomic_json(output / 'RESULT.json', result)
    print(json.dumps(result))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    run()
