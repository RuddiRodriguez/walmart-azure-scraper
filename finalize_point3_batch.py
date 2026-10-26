"""Wait once for bounded batch, export safe summaries, log and push generated evidence."""
from datetime import datetime,timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import time
from bs4 import BeautifulSoup
from diagnostic_capture import safe_url
from storage import atomic_json


def finish():
    root=Path('data/point3-20261026');public=Path('evidence/point3-20261026')
    with (root/'finalizer.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'finalized.json').exists():return
        deadline=time.monotonic()+10800
        while time.monotonic()<deadline:
            status=json.loads((root/'batch-status.json').read_text())
            if status['finished']:break
            time.sleep(30)
        else:raise RuntimeError('Finalizer bounded wait expired; inspect batch status')
        audits=[]
        for name in ['coverage-1','coverage-2','offers']:
            run=root/name
            if not (run/'report.json').exists():continue
            report=json.loads((run/'report.json').read_text())
            metadata=[]
            for path in sorted((run/'captures').glob('*.json')):
                item=json.loads(path.read_text())
                if item.get('body_file'):
                    body=(path.parent/item['body_file']).read_bytes()
                    assert hashlib.sha256(body).hexdigest()==item['body_sha256'] and len(body)==item['body_bytes']
                metadata.append({k:item[k] for k in ['id','kind','session','sequence','request','response','body_bytes','body_sha256','body_scope'] if k in item})
            destination=public/name;destination.mkdir(exist_ok=True)
            atomic_json(destination/'capture-metadata.json',metadata)
            summary={k:report[k] for k in ['mode','source_commit','source_hashes','source_sha256','started_utc','completed','seconds','limits','counts','error_type','full_coverage_complete'] if k in report}
            summary.update(original_body_hashes_verified=sum(bool(m.get('body_sha256')) for m in metadata),source_scope='Bounded live attempt with offline body integrity checks; not exhaustive coverage or independent offer-terms acceptance')
            if name.startswith('coverage'):
                pages=[]
                for entry in report.get('categories',[]):
                    if entry.get('native_snapshot_sha256'):
                        native=run/f'root-{len(pages)+1}.html'
                        assert hashlib.sha256(native.read_bytes()).hexdigest()==entry['native_snapshot_sha256']
                    selected={k:entry[k] for k in ['category','status','scope_review_only','page_title','observed_product_category_paths','visible_candidates','excluded_candidates','native_snapshot_sha256','fetch_context_verified','fetch_context','fetch_sequence'] if k in entry}
                    selected['url']=safe_url(entry['url'])
                    selected['discovered_child_urls']=[safe_url(u) for u in entry.get('discovered_child_urls',[])]
                    selected['decisions']=[{**{k:d[k] for k in ['action','reason','name'] if k in d},'url':safe_url(d['url'])} for d in entry.get('decisions',[]) if 'url' in d]
                    pages.append(selected)
                atomic_json(destination/'page-decisions.json',pages)
                summary.update(pages_reviewed=len(pages),full_coverage_complete=False)
            else:
                # Full unreviewed offer descriptions/unknown payloads remain private for agent terms review.
                summary.update(distinct_products_inspected=len({p['candidate_id'] for p in report.get('products',[])}),offer_candidates_passing_helper=len(report.get('verified_examples',[])),complete_offer_terms_review='Pending agent source review if any candidate exists; no invented examples')
                atomic_json(destination/'offer-candidates.json',[{k:p[k] for k in ['sequence','candidate_id','store_id','zip','intent','accepted','reason','description_visible_in_response','explicit_offer_price','current_local_price'] if k in p} for p in report.get('products',[])])
            atomic_json(destination/'summary.json',summary);audits.append(dict(phase=name,**summary))
        subprocess.run([__import__('sys').executable,'reconcile_coverage.py'],check=True,stdout=subprocess.DEVNULL)
        outcome=dict(source_commit=status['source_commit'],phase=status['phase'],finished_utc=status['finished_utc'],results=status['results'],error=status.get('error'),full_category_coverage_complete=False,genuine_offers_complete=False,large_sample_checks='See recovery-result and source-audited sample summaries where present; stopped attempts not complete',scope='Bounded requested milestones only. No full-catalog completion or live Azure claim.')
        atomic_json(public/'batch-outcome.json',outcome)
        for folder in [public,*[p for p in public.iterdir() if p.is_dir()]]:
            atomic_json(folder/'SHA256SUMS.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file() and p.name!='SHA256SUMS.json'})
        with Path('WORK_LOG.md').open('a') as stream:
            stream.write('\n## Point3 bounded batch completed/stopped\n'+json.dumps(outcome)+'\nSafe coverage/offer metadata/bodyhash checks exported;raw/native bodies private. Offerterms require source review if candidate exists. Fulltaxonomy/queuecoverage remains incomplete. Large sample completion only if recovery/independent source audits passed; failed attempt not labelled complete. Frozen producer untouched by finalizer.\n')
        subprocess.run(['git','add','WORK_LOG.md','evidence/point3-20261026','finalize_point3_batch.py'],check=True)
        manifest=Path('evidence/SHA256SUMS.json')
        names=subprocess.check_output(['git','ls-files'],text=True).splitlines()
        atomic_json(manifest,{n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in names if n!=str(manifest) and Path(n).is_file()})
        subprocess.run(['git','add',str(manifest)],check=True)
        subprocess.run(['git','diff','--cached','--check'],check=True)
        subprocess.run(['git','commit','-m','Record bounded point3 coverage offers and recovery repeat results'],check=True)
        subprocess.run(['git','-c','http.version=HTTP/1.1','-c','http.postBuffer=52428800','push','origin','main'],check=True)
        atomic_json(root/'finalized.json',dict(completed_utc=datetime.now(timezone.utc).isoformat(),pushed_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),outcome=outcome))


if __name__=='__main__':finish()
