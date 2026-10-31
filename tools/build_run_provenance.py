"""Build the client-facing run source and configuration index."""
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def evidence_commit(path):
    return subprocess.check_output(
        ['git', 'log', '-1', '--format=%H', '--', path], cwd=ROOT, text=True
    ).strip()


def named_runs():
    recovery_506 = read('evidence/point3-20261026/recovery-506/summary.json')
    repeat_506 = read('evidence/point3-20261026/repeat-506/summary.json')
    recovery_132 = read('evidence/latest-large-recovery-20261027/review.json')
    azure = read('evidence/azure-sequence-20261027/RESULT.json')
    oxylabs = read('evidence/oxylabs-bounded-20261030/RESULT.json')
    unblocker = read('evidence/web-unblocker-bounded-20261030/RESULT.json')
    offline = read('evidence/full-offline-regression-20261031/RESULT.json')
    return [
        {
            'name': '506-product interruption and recovery demonstration',
            'kind': 'historical bounded live demonstration',
            'source_commit': recovery_506['source_commit'],
            'configuration': 'evidence/point3-20261026/collection-plan.json',
            'result': 'evidence/point3-20261026/recovery-506/summary.json',
            'clean_current_version_run': False,
        },
        {
            'name': '506-product repeat demonstration',
            'kind': 'historical bounded live demonstration',
            'source_commit': repeat_506['source_commit'],
            'configuration': 'evidence/point3-20261026/collection-plan.json',
            'result': 'evidence/point3-20261026/repeat-506/summary.json',
            'clean_current_version_run': False,
        },
        {
            'name': '132-product interruption and recovery',
            'kind': 'historical bounded live recovery',
            'source_commit': recovery_132['source_commit'],
            'configuration': {
                'mode': recovery_132['mode'],
                'limits': recovery_132['limits'],
                'category_source': 'config/categories.csv',
            },
            'result': 'evidence/latest-large-recovery-20261027/review.json',
            'clean_current_version_run': False,
        },
        {
            'name': '132-product repeat',
            'kind': 'historical bounded live repeat',
            'source_commit': recovery_132['source_commit'],
            'source_commit_basis': 'The comparison and README record the same code, configuration signature and category file as the recovery run.',
            'configuration': {
                'sample_per_category': 12,
                'all_required_categories': True,
                'category_source': 'config/categories.csv',
            },
            'result': 'evidence/latest-large-repeat-20261027/comparison.json',
            'clean_current_version_run': False,
        },
        {
            'name': 'Azure West US 2 diagnostic',
            'kind': 'bounded Azure live diagnostic',
            'source_commit': azure['source_commits']['west_us_2'],
            'configuration': 'evidence/azure-sequence-20261027/COMMANDS.md',
            'exact_source': 'evidence/azure-sequence-20261027/source/run_azure_sequence-westus2-9101c81.py',
            'result': 'evidence/azure-sequence-20261027/RESULT.json',
        },
        {
            'name': 'Azure East US 2 diagnostic',
            'kind': 'bounded Azure live diagnostic',
            'source_commit': azure['source_commits']['east_us_2'],
            'configuration': 'evidence/azure-sequence-20261027/COMMANDS.md',
            'exact_source': 'evidence/azure-sequence-20261027/source/run_azure_sequence-eastus2-8f9a5c6.py',
            'result': 'evidence/azure-sequence-20261027/RESULT.json',
        },
        {
            'name': 'Oxylabs residential initial and fresh-session retry',
            'kind': 'bounded paid transport diagnostic',
            'source_commit': oxylabs['source_commit'],
            'configuration': {
                'transport': oxylabs['transport'],
                'limits': oxylabs['limits'],
                'account_controls': oxylabs['account_controls'],
            },
            'result': 'evidence/oxylabs-bounded-20261030/RESULT.json',
        },
        {
            'name': 'Oxylabs Web Unblocker diagnostic',
            'kind': 'bounded paid transport diagnostic',
            'source_commit': unblocker['source_commit'],
            'configuration': unblocker['request_scope'],
            'result': 'evidence/web-unblocker-bounded-20261030/RESULT.json',
        },
        {
            'name': 'Direct persistent store-session recovery',
            'kind': 'bounded live browser diagnostic',
            'source_commit': None,
            'source_commit_recorded': False,
            'evidence_commit': evidence_commit('evidence/store-session-recovery-20261030/RESULT.json'),
            'configuration': {
                'target': 'Store 100, ZIP 72712, PICKUP',
                'coverage_pages_attempted': 0,
                'private_persistent_profile': True,
            },
            'result': 'evidence/store-session-recovery-20261030/RESULT.json',
        },
        {
            'name': 'Scrape.do bounded product and search diagnostics',
            'kind': 'bounded provider API diagnostic',
            'source_commit': None,
            'source_commit_recorded': False,
            'evidence_commit': evidence_commit('evidence/scrapedo-bounded-20261030/RESULT.json'),
            'configuration': 'evidence/scrapedo-bounded-20261030/RESULT.json',
            'result': 'evidence/scrapedo-bounded-20261030/RESULT.json',
            'note': 'Manual provider requests; no repository diagnostic module was recorded.',
        },
        {
            'name': 'Bright Data bounded control input',
            'kind': 'bounded provider dataset diagnostic',
            'source_commit': None,
            'source_commit_recorded': False,
            'evidence_commit': evidence_commit('evidence/brightdata-bounded-20261030/RESULT.json'),
            'configuration': 'evidence/brightdata-bounded-20261030/RESULT.json',
            'result': 'evidence/brightdata-bounded-20261030/RESULT.json',
            'note': 'Provider dashboard input; no repository diagnostic module was recorded.',
        },
        {
            'name': 'Full offline regression',
            'kind': 'offline regression',
            'source_commit': offline['source_commit'],
            'configuration': 'Commands and evidence paths are recorded in the result file.',
            'result': 'evidence/full-offline-regression-20261031/RESULT.json',
        },
    ]


def coverage_batches():
    rows = []
    base = ROOT / 'evidence/point3-coverage-queue-20261026'
    for report_path in sorted(base.glob('batch-*/report.json')):
        report = json.loads(report_path.read_text())
        rows.append({
            'batch': report_path.parent.name,
            'source_commit': report.get('source_commit'),
            'source_commit_recorded': bool(report.get('source_commit')),
            'configuration': {
                'limits': report.get('limits'),
                'category': report.get('category'),
                'start_url': report.get('start_url'),
            },
            'result': str(report_path.relative_to(ROOT)),
        })
    return rows


def build():
    output = ROOT / 'evidence/final-package-20261101/RUN_PROVENANCE.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'scope': 'Every client-cited run plus every exported coverage batch with a report file.',
        'claim_boundary': 'A missing recorded source commit is shown as missing; it is not inferred from a later evidence commit.',
        'named_runs': named_runs(),
        'coverage_batches': coverage_batches(),
    }
    output.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({'named_runs': len(payload['named_runs']), 'coverage_batches': len(payload['coverage_batches'])}))


if __name__ == '__main__':
    build()
