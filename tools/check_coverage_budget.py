"""Offline coordinator restart/budget tests. No browser, network or Git writes."""
import json,sqlite3,tempfile,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import continue_coverage as worker
from storage import atomic_json


def check():
 checks=[]
 with tempfile.TemporaryDirectory() as folder:
  root=Path(folder)/'external'/'run';root.mkdir(parents=True)
  free=SimpleNamespace(free=100*worker.GIB)
  with patch.object(worker,'ROOT',root),patch.object(worker,'CODEX',root.parent),patch.object(worker,'EXTERNAL_DATA',root.parent),patch.object(Path,'is_mount',return_value=True),patch.object(worker.shutil,'disk_usage',return_value=free):worker.ensure_storage()
  try:
   with patch.object(worker,'ROOT',Path(folder)/'local'),patch.object(worker,'CODEX',root.parent),patch.object(worker,'EXTERNAL_DATA',root.parent),patch.object(Path,'is_mount',return_value=True),patch.object(worker.shutil,'disk_usage',return_value=free):worker.ensure_storage()
  except RuntimeError as error:assert 'relocated' in str(error)
  else:raise AssertionError('Local evidence path was accepted')
  low=SimpleNamespace(free=39*worker.GIB)
  try:
   with patch.object(worker,'ROOT',root),patch.object(worker,'CODEX',root.parent),patch.object(worker,'EXTERNAL_DATA',root.parent),patch.object(Path,'is_mount',return_value=True),patch.object(worker.shutil,'disk_usage',side_effect=[free,low]):worker.ensure_storage()
  except RuntimeError as error:assert 'CODEX free space' in str(error)
  else:raise AssertionError('Low CODEX space was accepted')
  try:
   with patch.object(worker,'ROOT',root),patch.object(worker,'CODEX',root.parent),patch.object(worker,'EXTERNAL_DATA',root.parent),patch.object(Path,'is_mount',return_value=True),patch.object(worker.shutil,'disk_usage',return_value=SimpleNamespace(free=59*worker.GIB)):worker.ensure_storage()
  except RuntimeError as error:assert 'Mac free space' in str(error)
  else:raise AssertionError('Low Mac space was accepted')
  checks+=['External evidence location required','60 GiB Mac reserve enforced','40 GiB CODEX reserve enforced']
 with tempfile.TemporaryDirectory(dir='data') as folder:
  root=Path(folder);public=root/'public';public.mkdir()
  deadline=time.time()-10
  atomic_json(root/'worker-status.json',dict(batches=20,pages_attempted=1700,max_seconds=43200,max_pages=2000,deadline_unix=deadline))
  with patch.object(worker,'ROOT',root),patch.object(worker,'PUBLIC',public),patch.object(worker,'ensure_storage'),patch.object(worker.psutil,'process_iter',return_value=[]),patch.object(worker.subprocess,'Popen') as start:
   worker.run();start.assert_not_called()
  result=json.loads((root/'worker-status.json').read_text())
  assert result['deadline_unix']==deadline and result['pages_attempted']==1700 and result['phase']=='original_finite_work_budget_reached' and result['user_paused'] is False
  checks+=['Restart keeps original expired deadline','Restart keeps consumed page allowance','Expired budget launches no job']
 with tempfile.TemporaryDirectory(dir='data') as folder:
  root=Path(folder);public=root/'public';public.mkdir();batch=root/'batch-inflight';batch.mkdir()
  deadline=time.time()+1000
  atomic_json(root/'worker-status.json',dict(batches=1,pages_attempted=80,max_seconds=43200,max_pages=2000,deadline_unix=deadline,latest_batch='prior'))
  atomic_json(batch/'report.json',dict(pages=[{},{}],queue_counts={'pending':0},scope_counts={}))
  db=sqlite3.connect(root/'queue.sqlite');db.execute('CREATE TABLE pages(status TEXT)');db.commit();db.close()
  with patch.object(worker,'ROOT',root),patch.object(worker,'PUBLIC',public),patch.object(worker,'ensure_storage'),patch.object(worker.psutil,'process_iter',return_value=[]),patch.object(worker,'export_batch',side_effect=RuntimeError('Synthetic export interruption')):
   worker.run()
  assert json.loads((root/'worker-status.json').read_text())['pages_attempted']==82
  def exported(b,r,s):
   (public/b.name).mkdir(exist_ok=True);atomic_json(public/b.name/'report.json',r)
  with patch.object(worker,'ROOT',root),patch.object(worker,'PUBLIC',public),patch.object(worker,'ensure_storage'),patch.object(worker.psutil,'process_iter',return_value=[]),patch.object(worker,'export_batch',side_effect=exported),patch.object(worker.subprocess,'Popen') as start:
   worker.run();start.assert_not_called()
  result=json.loads((root/'worker-status.json').read_text())
  assert result['pages_attempted']==82 and result['batches']==2 and result['deadline_unix']==deadline
  checks+=['Finished orphan batch adopted once','Interrupted evidence export does not double-count pages on restart','Adoption preserves original deadline and starts no duplicate job']
 result=dict(passed=True,checks=checks,live_requests=0)
 out=Path('evidence/queue-growth-audit-20261026');out.mkdir(exist_ok=True);atomic_json(out/'budget-checks.json',result);print(json.dumps(result))


if __name__=='__main__':check()
