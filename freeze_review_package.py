"""Archive a frozen Git version and verify contents without scraping or publishing."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def build(version, output):
    if not output.resolve().is_relative_to(Path('data').resolve()):
        raise ValueError('Local archive must stay under ignored data/')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError('Archive already exists')
    commit = subprocess.check_output(['git', 'rev-parse', version + '^{commit}'], text=True).strip()
    subprocess.run(['git', 'archive', '--format=zip', '--output=' + str(output), version], check=True)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive CRC check failed')
        names = archive.namelist()
        forbidden = [n for n in names if n.startswith(('data/', '.git/', '.venv/')) or n.endswith(('.body', '.redaction-draft.html', '.log')) or '/.env' in n or n == '.env']
        if forbidden:
            raise ValueError('Private/runtime files in archive: ' + repr(forbidden))
        manifest = json.loads(archive.read('evidence/SHA256SUMS.json'))
        for name, expected in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('File manifest mismatch: ' + name)
        files = {n for n in names if not n.endswith('/')}
        if files != set(manifest) | {'evidence/SHA256SUMS.json'}:
            raise ValueError('Archive inventory differs from manifest')
        datasets = []
        for folder in ['controlled-skip-invalid-20261025', 'controlled-skip-invalid-repeat-20261025', 'step8-controlled-recovery-20261026']:
            base = 'evidence/' + folder + '/'
            rows = json.loads(archive.read(base + 'products.json'))
            summary = json.loads(archive.read(base + 'summary.json'))
            if len(rows) != summary['accepted_records'] or len({r['url'] for r in rows}) != len(rows) or not summary['accepted_evidence_passed'] or not summary['sample_accepted']:
                raise ValueError('Dataset/export audit mismatch: ' + folder)
            datasets.append(dict(folder=folder, records=len(rows), source_commit=summary['source_commit'],
                                 json_sha256=hashlib.sha256(archive.read(base + 'products.json')).hexdigest()))
        recovery = json.loads(archive.read('evidence/step8-controlled-recovery-20261026/recovery-result.json'))
        if not recovery['passed'] or not all(recovery['checks'].values()):
            raise ValueError('Recovery evidence failed')
    result = dict(version=version, source_commit=commit, filename=output.name, bytes=output.stat().st_size,
                  sha256=hashlib.sha256(output.read_bytes()).hexdigest(), zip_crc_passed=True,
                  file_manifest_verified=len(manifest), archive_inventory_verified=True,
                  private_runtime_files_excluded=True, datasets=datasets, recovery_checks=len(recovery['checks']),
                  scope='Offline archive/manifest/export verification; no new live collection or raw-body replay',
                  client_message_sent=False, contest_submitted=False, azure_executed=False)
    output.with_suffix('.receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.version, args.output)
