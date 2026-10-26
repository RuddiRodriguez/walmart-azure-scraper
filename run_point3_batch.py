"""One sequential, bounded point3 batch. No client operations or automatic retry loops."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime,timezone
import psutil
from storage import atomic_json


def run():
    root=Path('data/point3-20261026');root.mkdir(exist_ok=False)
    public=Path('evidence/point3-20261026')
    version=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    producer=['controlled_collection.py','retention.py','extract.py','browser.py','scrape.py','storage.py','validate.py','diagnostic_capture.py','capture_store_drift.py']
    hashes={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in producer}
    status=dict(source_commit=version,started_utc=datetime.now(timezone.utc).isoformat(),phase='starting',results=[],finished=False)
    def save():atomic_json(root/'batch-status.json',status)
    def command(name,args,seconds):
        if any(hashlib.sha256(Path(n).read_bytes()).hexdigest()!=h for n,h in hashes.items()):raise RuntimeError('Frozen producer changed; batch stopped')
        status.update(phase=name);save()
        with (root/(name+'.log')).open('w') as log:
            process=subprocess.Popen([sys.executable,*args],stdout=log,stderr=subprocess.STDOUT)
            try:process.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                for child in psutil.Process(process.pid).children(recursive=True):
                    try:child.kill()
                    except psutil.NoSuchProcess:pass
                process.kill();process.wait()
                raise RuntimeError(name+' outer runtime guard reached')
        return process.returncode
    def safety(report):
        text=str(report.get('error','')).lower()
        if any(x in text for x in ['access blocked','challenge','disk reserve','body budget']):raise RuntimeError('Resource/access stop condition; see phase report')
    save()
    try:
        for index in [1,2]:
            directory=root/f'coverage-{index}'
            code=command(f'coverage-{index}',['review_category_coverage.py','--output',str(directory),'--plan',str(public/f'coverage-case-{index}.json'),'--seconds','180'],210)
            report=json.loads((directory/'report.json').read_text());safety(report)
            status['results'].append(dict(phase=f'coverage-{index}',completed=report['completed'],error=report.get('error'),exit_code=code));save()
        directory=root/'offers'
        code=command('offers',['review_live_offers.py','--output',str(directory),'--expanded'],630)
        report=json.loads((directory/'report.json').read_text());safety(report)
        status['results'].append(dict(phase='offers',completed=report['completed'],genuine_examples=len(report['verified_examples']),error=report.get('error'),exit_code=code));save()
        plan=public/'collection-plan.json'
        baseline=root/'recovery';first=baseline/'collection';first_public=public/'recovery-506'
        command('recovery-506',['run_controlled_recovery.py','--output',str(baseline),'--plan',str(plan)],3630)
        recovery=json.loads((baseline/'recovery-result.json').read_text())
        safe={k:v for k,v in recovery.items() if k!='command'}
        atomic_json(public/'recovery-result.json',safe)
        if not recovery['passed']:raise RuntimeError('Recovery did not pass; no repeated large collection queued')
        command('audit-recovery',['audit_controlled_collection.py','--run',str(first),'--evidence',str(first_public)],180)
        summary=json.loads((first_public/'summary.json').read_text())
        if not summary['sample_accepted']:raise RuntimeError('First sample audit failed; repeat cancelled')
        shutil.copyfile(plan,first_public/'plan.json')
        status['results'].append(dict(phase='recovery-506',completed=True,records=summary['accepted_records'],seconds=summary['seconds'],source_audit_passed=True));save()
        repeat=root/'repeat';repeat_public=public/'repeat-506';repeat_public.mkdir(exist_ok=True)
        shutil.copyfile(plan,repeat_public/'plan.json')
        atomic_json(repeat_public/'preflight.json',dict(baseline_dataset_sha256=hashlib.sha256((first_public/'products.json').read_bytes()).hexdigest(),source_commit=version,producer_hashes=hashes))
        command('repeat-506',['controlled_collection.py','--output',str(repeat),'--plan',str(plan)],3630)
        command('audit-repeat',['audit_controlled_collection.py','--run',str(repeat),'--evidence',str(repeat_public)],180)
        summary=json.loads((repeat_public/'summary.json').read_text())
        if not summary['sample_accepted']:raise RuntimeError('Repeat did not pass source audit')
        command('compare',['compare_controlled_collections.py','--baseline',str(first_public),'--repeat',str(repeat_public)],60)
        status['results'].append(dict(phase='repeat-506',completed=True,records=summary['accepted_records'],seconds=summary['seconds'],source_audit_passed=True))
        status['phase']='bounded_batch_complete'
    except Exception as error:
        status.update(phase='stopped',error=str(error),error_type=type(error).__name__)
    finally:
        status.update(finished=True,finished_utc=datetime.now(timezone.utc).isoformat());save()
    print(json.dumps(status))


if __name__=='__main__':
    os.umask(0o077)
    run()
