"""Run bounded live batches after taxonomy cleanup."""
import argparse,fcntl,json,sqlite3,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from continue_coverage import ensure_storage,export_batch
from storage import atomic_json

ROOT=Path('data/full-coverage-20261026')
SECONDS=1800


def counts():
    db=sqlite3.connect(ROOT/'queue.sqlite');result=dict(db.execute('SELECT status,count(*) FROM pages GROUP BY status'));db.close();return result


def run(batches,pages,output):
    ensure_storage();output.mkdir(parents=True,exist_ok=True)
    lock=(ROOT/'worker.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    started=datetime.now(timezone.utc).isoformat();before=counts();results=[];growth_streak=0
    for number in range(1,batches+1):
        ensure_storage();existing=set(ROOT.glob('batch-*'));pending=counts().get('pending',0)
        with (ROOT/'taxonomy-trial.log').open('a') as log:
            process=subprocess.run([sys.executable,'coverage_queue.py','--pages',str(pages),'--seconds',str(SECONDS)],stdout=log,stderr=subprocess.STDOUT,timeout=SECONDS+60)
        created=set(ROOT.glob('batch-*'))-existing
        if len(created)!=1:raise RuntimeError('Unexpected taxonomy trial batch count')
        batch=created.pop();report=json.loads((batch/'report.json').read_text());after=report['queue_counts'];processed=len(report['pages']);new=report.get('new_page_identities',0)
        growth_streak=growth_streak+1 if processed and after.get('pending',0)>=pending else 0
        results.append(dict(number=number,batch=batch.name,pages=processed,new_pages=new,pending_before=pending,pending_after=after.get('pending',0),failed_after=after.get('failed',0),stop_reason=report.get('stop_reason'),offer_observations=len(report.get('offer_observations',[]))))
        progress=dict(started_utc=started,finished=False,limits=dict(batches=batches,pages_per_batch=pages,seconds_per_batch=SECONDS),results=results)
        atomic_json(output/'progress.json',progress)
        status=json.loads((ROOT/'worker-status.json').read_text());status.update(phase='client_full_coverage_continuation',finished=False,queue_counts=after,coverage_completion=progress)
        atomic_json(ROOT/'worker-status.json',status);export_batch(batch,report,status)
        if not processed:break
        if process.returncode or report.get('stop_reason') or growth_streak>=2:break
    final=counts();summary=dict(started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),finished=True,limits=dict(batches=batches,pages_per_batch=pages,seconds_per_batch=SECONDS),status_before=before,status_after=final,results=results,queue_shrank=final.get('pending',0)<before.get('pending',0),growth_stop_triggered=growth_streak>=2,live_scope='User-authorized bounded taxonomy batches; no full-coverage claim')
    atomic_json(output/'summary.json',summary)
    status=json.loads((ROOT/'worker-status.json').read_text());status.update(phase='taxonomy_trial_complete' if len(results)==batches else 'taxonomy_trial_stopped',finished=True,queue_counts=final,taxonomy_trial=summary);atomic_json(ROOT/'worker-status.json',status)
    lock.close();print(json.dumps(summary))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--batches',type=int,default=2);parser.add_argument('--pages',type=int,default=20);parser.add_argument('--output',type=Path,default=Path('evidence/taxonomy-trial-20261027'))
    args=parser.parse_args();run(args.batches,args.pages,args.output)
