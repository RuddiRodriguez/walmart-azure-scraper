"""Finite persistent coverage continuations, safe evidence export and commits."""
import fcntl,hashlib,json,sqlite3,subprocess,sys,time
from pathlib import Path
import psutil
from storage import atomic_json
from diagnostic_capture import safe_url


def run():
 root=Path('data/full-coverage-20261026');public=Path('evidence/point3-coverage-queue-20261026')
 lock=(root/'worker.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 started=time.monotonic();status=dict(phase='starting',batches=0,pages_attempted=0,finished=False,max_seconds=43200,max_pages=2000)
 try:
  while time.monotonic()-started<43200 and status['pages_attempted']<2000:
   db=sqlite3.connect(root/'queue.sqlite');pending=db.execute("SELECT count(*) FROM pages WHERE status='pending'").fetchone()[0];db.close()
   if not pending:status['phase']='queue_exhausted_review_remaining_gaps';break
   status['phase']='walking';atomic_json(root/'worker-status.json',status)
   before=set(root.glob('batch-*'));remaining=int(43200-(time.monotonic()-started));maximum=min(80,2000-status['pages_attempted'])
   with (root/'worker.log').open('a') as log:
    process=subprocess.Popen([sys.executable,'coverage_queue.py','--pages',str(maximum),'--seconds',str(min(5400,remaining))],stdout=log,stderr=subprocess.STDOUT)
    try:process.wait(timeout=min(5400,remaining)+30)
    except subprocess.TimeoutExpired:
     for child in psutil.Process(process.pid).children(recursive=True):
      try:child.kill()
      except psutil.NoSuchProcess:pass
     process.kill();process.wait();raise RuntimeError('Coverage outer runtime guard reached')
   new=set(root.glob('batch-*'))-before
   if len(new)!=1:raise RuntimeError('Unexpected batch count; do not duplicate running work')
   batch=new.pop();report=json.loads((batch/'report.json').read_text());status['batches']+=1;status['pages_attempted']+=len(report['pages'])
   status.update(queue_counts=report['queue_counts'],scope_counts=report['scope_counts'],latest_batch=batch.name,seconds=round(time.monotonic()-started,1));atomic_json(root/'worker-status.json',status)
   dest=public/batch.name;dest.mkdir(exist_ok=True);metadata=[]
   for path in (batch/'captures').glob('*.json'):
    item=json.loads(path.read_text())
    if item.get('body_file'):
     body=(path.parent/item['body_file']).read_bytes();assert hashlib.sha256(body).hexdigest()==item['body_sha256']
    metadata.append({k:item[k] for k in ['id','session','kind','sequence','request','response','body_sha256','body_bytes','body_scope'] if k in item})
   atomic_json(dest/'capture-metadata.json',metadata);atomic_json(dest/'report.json',report)
   atomic_json(dest/'native-hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in batch.glob('native-*.html')})
   db=sqlite3.connect(root/'queue.sqlite');columns=[c[1] for c in db.execute('PRAGMA table_info(pages)')]
   ledger=[dict(zip(columns,row)) for row in db.execute('SELECT * FROM pages ORDER BY category,key')]
   for row in ledger:row['url']=safe_url(row['url'])
   atomic_json(public/'persistent-page-ledger.json',ledger)
   atomic_json(public/'scope-proofs.json',[dict(category=c,leaf=leaf,decision=d,actual_id=a,breadcrumb=json.loads(b),source=s) for c,leaf,d,a,b,s in db.execute('SELECT * FROM scope_proofs ORDER BY category,leaf')]);db.close()
   atomic_json(public/'worker-status.json',status)
   with Path('WORK_LOG.md').open('a') as log:log.write('\n## Coverage continuation result\n'+json.dumps(status)+'\nListing/category review only. Pending/failed/scope-unverified remain open. Raw bodies/native pages private. Offer candidates require source/terms review; no invented examples or full-catalog claim.\n')
   for directory in [public,dest]:atomic_json(directory/'SHA256SUMS.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir()) if p.is_file() and p.name!='SHA256SUMS.json'})
   subprocess.run(['git','add','WORK_LOG.md','evidence/point3-coverage-queue-20261026'],check=True)
   manifest=Path('evidence/SHA256SUMS.json');names=subprocess.check_output(['git','ls-files'],text=True).splitlines();atomic_json(manifest,{n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in names if n!=str(manifest) and Path(n).is_file()})
   subprocess.run(['git','add',str(manifest)],check=True);subprocess.run(['git','diff','--cached','--check'],check=True);subprocess.run(['git','commit','-m','Record persistent coverage continuation and actual taxonomy evidence'],check=True)
   subprocess.run(['git','-c','http.version=HTTP/1.1','-c','http.postBuffer=52428800','push','origin','main'],check=True)
   if report.get('stop_reason'):raise RuntimeError(report['stop_reason'])
   if process.returncode:raise RuntimeError('Walker failed; inspect private worker log')
   if not report['pages']:raise RuntimeError('No page progress; stop automatic continuations')
   if any(o.get('qualified_candidate') for o in report.get('offer_observations',[])):status['phase']='offer_candidate_ready_for_source_review';break
  else:status['phase']='finite_work_budget_reached'
 except Exception as error:status.update(phase='stopped',error=str(error))
 finally:
  status.update(finished=True,seconds=round(time.monotonic()-started,1));atomic_json(root/'worker-status.json',status);lock.close()


if __name__=='__main__':run()
