"""Finite persistent coverage continuations; original budget survives audit/restart."""
import fcntl,hashlib,json,shutil,sqlite3,subprocess,sys,time
from pathlib import Path
import psutil
from storage import atomic_json
from diagnostic_capture import safe_url

ROOT=Path('data/full-coverage-20261026')
PUBLIC=Path('evidence/point3-coverage-queue-20261026')
CODEX=Path('/Volumes/CODEX')
EXTERNAL_DATA=CODEX/'Walmart_Scraper_Private_Evidence'
GIB=2**30


def ensure_storage():
 if not CODEX.is_mount():raise RuntimeError('CODEX evidence drive is not mounted')
 if not ROOT.resolve().is_relative_to(EXTERNAL_DATA.resolve()):raise RuntimeError('Private evidence has not been verified and relocated to CODEX')
 if shutil.disk_usage('/').free<60*GIB:raise RuntimeError('Mac free space is below 60 GiB')
 if shutil.disk_usage(CODEX).free<40*GIB:raise RuntimeError('CODEX free space is below 40 GiB')


def next_growth_streak(previous,pages,new_pages):
 return previous+1 if pages and new_pages>=pages else 0


def export_batch(batch,report,status):
 dest=PUBLIC/batch.name;dest.mkdir(exist_ok=True);metadata=[]
 for path in (batch/'captures').glob('*.json'):
  item=json.loads(path.read_text())
  if item.get('body_file'):
   body=(path.parent/item['body_file']).read_bytes();assert hashlib.sha256(body).hexdigest()==item['body_sha256']
  metadata.append({k:item[k] for k in ['id','session','kind','sequence','request','response','body_sha256','body_bytes','body_scope'] if k in item})
 atomic_json(dest/'capture-metadata.json',metadata);atomic_json(dest/'report.json',report)
 atomic_json(dest/'native-hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in batch.glob('native-*.html')})
 db=sqlite3.connect(ROOT/'queue.sqlite');columns=[c[1] for c in db.execute('PRAGMA table_info(pages)')]
 ledger=[dict(zip(columns,row)) for row in db.execute('SELECT * FROM pages ORDER BY category,key')]
 for row in ledger:row['url']=safe_url(row['url'])
 atomic_json(PUBLIC/'persistent-page-ledger.json',ledger)
 atomic_json(PUBLIC/'scope-proofs.json',[dict(category=c,leaf=leaf,decision=d,actual_id=a,breadcrumb=json.loads(b),source=s) for c,leaf,d,a,b,s in db.execute('SELECT * FROM scope_proofs ORDER BY category,leaf')]);db.close()
 atomic_json(PUBLIC/'worker-status.json',status)
 with Path('WORK_LOG.md').open('a') as log:log.write('\n## Coverage continuation result\n'+json.dumps(status)+'\nListing/category review only. Pending/failed/scope-unverified remain open. Raw bodies/native pages private.\n')
 for directory in [PUBLIC,dest]:atomic_json(directory/'SHA256SUMS.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir()) if p.is_file() and p.name!='SHA256SUMS.json'})
 subprocess.run(['git','add','WORK_LOG.md',str(PUBLIC)],check=True)
 manifest=Path('evidence/SHA256SUMS.json');names=subprocess.check_output(['git','ls-files'],text=True).splitlines();atomic_json(manifest,{n:hashlib.sha256(subprocess.check_output(['git','show',f':{n}'])).hexdigest() for n in names if n!=str(manifest)})
 subprocess.run(['git','add',str(manifest)],check=True);subprocess.run(['git','diff','--cached','--check'],check=True);subprocess.run(['git','commit','-m','Record persistent coverage continuation and actual taxonomy evidence'],check=True)
 subprocess.run(['git','-c','http.version=HTTP/1.1','-c','http.postBuffer=52428800','push','origin','main'],check=True)


def run():
 lock=(ROOT/'worker.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 saved=ROOT/'worker-status.json'
 status=json.loads(saved.read_text()) if saved.exists() else dict(batches=0,pages_attempted=0,max_seconds=43200,max_pages=2000)
 status.setdefault('deadline_unix',time.time()+status['max_seconds'])
 status.setdefault('accounted_batches',[status['latest_batch']] if status.get('latest_batch') else [])
 status.update(phase='resuming',finished=False);status.pop('error',None)
 frozen={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in ['coverage_queue.py','browser.py','extract.py']}
 def save():
  status['seconds']=round(status['max_seconds']-(status['deadline_unix']-time.time()),1);atomic_json(saved,status)
 def completed(batch):
  report=json.loads((batch/'report.json').read_text())
  if batch.name not in status['accounted_batches']:
   status['batches']+=1;status['pages_attempted']+=len(report['pages']);status['accounted_batches'].append(batch.name)
  pages=len(report['pages']);new=report.get('new_page_identities',0)
  status['queue_growth_streak']=next_growth_streak(status.get('queue_growth_streak',0),pages,new)
  status.update(queue_counts=report['queue_counts'],scope_counts=report['scope_counts'],latest_batch=batch.name,last_batch_pages=pages,last_batch_new_pages=new);save();export_batch(batch,report,status)
  if status['queue_growth_streak']>=2:raise RuntimeError('Queue did not shrink for two batches; offline taxonomy review required')
  if report.get('stop_reason'):
   if report['stop_reason']=='Bounded coverage runtime reached':status['phase']='original_finite_work_budget_reached';save();return False
   raise RuntimeError(report['stop_reason'])
  if not report['pages']:raise RuntimeError('No page progress')
  return any(o.get('qualified_candidate') for o in report.get('offer_observations',[]))
 try:
  if (ROOT/'USER_PAUSED').exists():status.update(phase='paused_by_user_storage_cleanup',user_paused=True);return
  status['user_paused']=False
  ensure_storage()
  # An audit may stop only the coordinator while its current child finishes safely.
  running=[p for p in psutil.process_iter(['cmdline']) if 'coverage_queue.py' in (p.info['cmdline'] or [])]
  if len(running)>1:raise RuntimeError('Multiple walkers; refuse duplicate work')
  if running:
   status['phase']='waiting_current_batch_finish';save();running[0].wait(timeout=max(1,min(5430,status['deadline_unix']-time.time())))
  for batch in sorted(ROOT.glob('batch-*')):
   if not (PUBLIC/batch.name/'report.json').exists() and (batch/'report.json').exists():
    if completed(batch):status['phase']='offer_candidate_ready_for_source_review';return
  while time.time()<status['deadline_unix'] and status['pages_attempted']<status['max_pages']:
   if any(hashlib.sha256(Path(n).read_bytes()).hexdigest()!=h for n,h in frozen.items()):raise RuntimeError('Walker code changed; review before continuing')
   db=sqlite3.connect(ROOT/'queue.sqlite');pending=db.execute("SELECT count(*) FROM pages WHERE status='pending'").fetchone()[0];db.close()
   if not pending:status['phase']='queue_exhausted_review_remaining_gaps';break
   status['phase']='walking';save();before=set(ROOT.glob('batch-*'))
   remaining=int(status['deadline_unix']-time.time());maximum=min(40,status['max_pages']-status['pages_attempted'])
   if remaining<1:break
   with (ROOT/'worker.log').open('a') as log:
    process=subprocess.Popen([sys.executable,'coverage_queue.py','--pages',str(maximum),'--seconds',str(min(5400,remaining))],stdout=log,stderr=subprocess.STDOUT)
    try:process.wait(timeout=min(5400,remaining)+30)
    except subprocess.TimeoutExpired:
     for child in psutil.Process(process.pid).children(recursive=True):
      try:child.kill()
      except psutil.NoSuchProcess:pass
     process.kill();process.wait();raise RuntimeError('Coverage outer runtime guard reached')
   new=set(ROOT.glob('batch-*'))-before
   if len(new)!=1:raise RuntimeError('Unexpected batch count')
   ensure_storage()
   if completed(new.pop()):status['phase']='offer_candidate_ready_for_source_review';break
   if process.returncode:raise RuntimeError('Walker failed; inspect private worker log')
  else:status['phase']='original_finite_work_budget_reached'
 except Exception as error:status.update(phase='stopped',error=str(error))
 finally:status['finished']=True;save();lock.close()


if __name__=='__main__':run()
