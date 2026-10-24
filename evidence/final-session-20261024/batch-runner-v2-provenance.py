"""Execute already-authorized review stages; no client communication or publication."""
import json,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
import psutil
root=Path.cwd();python=sys.executable;session=root/'data/final-session-20261024'
state={'started_utc':datetime.now(timezone.utc).isoformat(),'stages':[]}
def save():
 (session/'batch-status.json').write_text(json.dumps(state,indent=2)+'\n')
def wait_existing(pid):
 try:
  process=psutil.Process(pid)
  while process.is_running() and process.status()!=psutil.STATUS_ZOMBIE:time.sleep(15)
 except psutil.NoSuchProcess:pass
def finish(name,output,returncode=None):
 base=output/'100';pointer=json.loads((base/'active-sample.json').read_text());run=base/'runs'/pointer['run_id']
 destination=root/'evidence/final-session-20261024'/name
 export=subprocess.run([python,'export_run_evidence.py',str(run),str(destination)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (session/(name+'-export.log')).write_text(export.stdout)
 report=json.loads((run/'report.json').read_text()) if (run/'report.json').exists() else json.loads((run/'failure.json').read_text())
 rows=json.loads((run/('products.json' if (run/'products.json').exists() else 'products.partial.json')).read_text())
 audit=None
 if rows and export.returncode==0:
  check=subprocess.run([python,'audit_run.py',str(destination)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  (session/(name+'-audit.log')).write_text(check.stdout);audit=check.returncode==0
 banner=output/'banner-rejection/probe.json'
 if banner.exists():
  (destination/'banner-rejection.json').write_bytes(banner.read_bytes())
 probe=output/'rejection-probe/probe.json'
 if probe.exists():
  (destination/'rejection-probe.json').write_bytes(probe.read_bytes())
 result={'stage':name,'records':len(rows),'sample_passed':report.get('sample_validation',{}).get('passed',False),
         'source_audit_passed':audit,'returncode':returncode,'error':report.get('error'),
         'active_seconds':report.get('active_seconds'),'run':str(run.relative_to(root)),'evidence':str(destination.relative_to(root)),
         'signature':report.get('signature'),'finished_utc':datetime.now(timezone.utc).isoformat()}
 state['stages'].append(result);save()
 with (root/'WORK_LOG.md').open('a') as stream:stream.write('\nBatch stage result: '+json.dumps(result)+'\n')
 print(json.dumps(result),flush=True)
 return result['sample_passed'] and audit is True

def launch(name,sample,cutoff):
 output=session/name;log=(session/(name+'.log')).open('w')
 collector=subprocess.Popen([python,'-u','probe_collection_context.py','--config',str(session/'trace-config.json'),'--sample',str(sample),'--output',str(output)],stdout=log,stderr=subprocess.STDOUT)
 state['active']={'stage':name,'pid':collector.pid,'sample_per_category':sample,'cutoff_utc':cutoff};save()
 base=output/'100'
 while collector.poll() is None and not (base/'active-sample.json').exists():time.sleep(0.5)
 guard=None;guardlog=None
 if (base/'active-sample.json').exists() and collector.poll() is None:
  pointer=json.loads((base/'active-sample.json').read_text());run=base/'runs'/pointer['run_id'];guardlog=(session/(name+'-resources.log')).open('w')
  guard=subprocess.Popen([python,'-u','guard_review_disk.py',str(collector.pid),str(run),'--reserve-gib','8','--stop-at',cutoff],stdout=guardlog,stderr=subprocess.STDOUT)
 code=collector.wait();log.close()
 if guard:guard.wait();guardlog.close()
 state.pop('active',None)
 return finish(name,output,code)

state=json.loads((session/'batch-status.json').read_text())
if not launch('fresh-506-c',46,'2026-10-24T13:51:31+00:00'):raise SystemExit(1)
state['completed_requested_batch']=True;save()
