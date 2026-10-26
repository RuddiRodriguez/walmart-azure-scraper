"""Offline ledger of observed category links/pages; never infer exhaustive coverage."""
import csv
import json
from collections import Counter
from pathlib import Path
from extract import category_id
from storage import atomic_json,page_url


def reconcile():
    output=Path('evidence/point3-20261026');output.mkdir(exist_ok=True)
    roots={r['Category (Auto)']:page_url(r['URL']) for r in csv.DictReader(Path('config/categories.csv').open())}
    nodes={}
    def node(category,url):
        key=(category,page_url(url))
        return nodes.setdefault(key,dict(category=category,url=key[1],observed_in=[],visits=[],decisions=[]))
    for category,url in roots.items():node(category,url)['required_root']=True
    files=set(Path('evidence').glob('**/page-decisions.json'))
    files.update(Path('evidence/corrected-plan-20261025').glob('**/root-decisions.json'))
    files.update(Path('evidence/corrected-plan-20261025').glob('**/descendant-decisions.json'))
    for file in sorted(files):
        entries=json.loads(file.read_text())
        if not isinstance(entries,list):continue
        for entry in entries:
            category=entry.get('category');url=entry.get('url')
            if category not in roots or not url:continue
            item=node(category,url)
            item['visits'].append(dict(evidence=str(file),status=entry.get('status','recorded'),error=entry.get('error'),listing_sequence=entry.get('listing_sequence',entry.get('fetch_sequence'))))
            for decision in entry.get('decisions',[]):
                if not decision.get('url'):continue
                child=node(category,decision['url']);child['observed_in'].append(dict(parent=page_url(url),evidence=str(file)))
                child['decisions'].append({k:decision[k] for k in ['action','reason','name'] if k in decision})
            for link in entry.get('discovered_child_urls',[]):
                child=node(category,link);child['observed_in'].append(dict(parent=page_url(url),evidence=str(file)))
    unresolved_file=Path('evidence/corrected-plan-20261025/step6-followup-scope/remaining-decisions.json')
    for entry in json.loads(unresolved_file.read_text()):
        node(entry['category'],entry['url'])['prior_scope_status']=entry['classification']
    leaf_proof={}
    for (category,url),item in nodes.items():
        ids=category_id(url).split('_')
        if category_id(roots[category]) in ids[:-1]:leaf_proof[(category,ids[-1])]=url
    for (category,url),item in nodes.items():
        ids=category_id(url).split('_');root_id=category_id(roots[category])
        proof=leaf_proof.get((category,ids[-1]))
        if item.get('required_root') or category_id(url)==root_id:item['scope']='required_root'
        elif root_id in ids[:-1]:item['scope']='observed_descendant_id'
        elif proof:item.update(scope='observed_leaf_alias_contents_unverified',alias_evidence_url=proof)
        else:item['scope']='unresolved_scope'
        statuses={v['status'] for v in item['visits']}
        if statuses & {'reviewed','root_reviewed_children_not_crawled'}:item['visit_status']='reviewed_page_only'
        elif item['visits']:item['visit_status']='attempted_not_verified'
        else:item['visit_status']='not_visited'
        # Only original logged exclusions are preserved; uncertain links never silently dropped.
        item['explicit_exclusion_reasons']=sorted({d['reason'] for d in item['decisions'] if d.get('action')=='excluded' and d.get('reason')})
    ledger=sorted(nodes.values(),key=lambda v:(v['category'],v['url']))
    summary=dict(mode='Offline reconciliation of known observed links and dated page evidence; not complete retailer taxonomy',
                 source_files=len(files),observed_category_url_associations=len(ledger),unique_urls=len({n['url'] for n in ledger}),
                 scope_counts=dict(Counter(n['scope'] for n in ledger)),visit_counts=dict(Counter(n['visit_status'] for n in ledger)),
                 per_category={name:dict(Counter(n['visit_status'] for n in ledger if n['category']==name)) for name in roots},
                 full_coverage_complete=False,live_requests=0,
                 limitation='Visited page does not prove its descendants or pagination exhausted; failed/empty pages remain unresolved. Aliases retain distinct records. Newly undiscovered pages are unknown.')
    atomic_json(output/'coverage-ledger.json',ledger);atomic_json(output/'coverage-summary.json',summary)
    # Two observed aliases with explicit matching descendant ID evidence, one category each.
    plan=[]
    for category in ['Personal Care','Beauty']:
        options=[n for n in ledger if n['category']==category and n.get('prior_scope_status') and n.get('alias_evidence_url') and n['visit_status']=='not_visited']
        if options:
            chosen=min(options,key=lambda n:(len(n['url']),n['url']))
            plan.append(dict(category=category,url=chosen['url'],scope_evidence_url=chosen['alias_evidence_url'],reason='Previously unresolved observed landing; matching observed descendant leaf ID, contents require live verification'))
    if not plan:
        references=json.loads(unresolved_file.read_text())
        for category,leaf in [('Personal Care','5756015'),('Beauty','1333655')]:
            chosen=next(r for r in references if r['category']==category and category_id(r['url'])==leaf)
            plan.append(dict(category=category,url=chosen['url'],scope_review_only=True,source_evidence=str(unresolved_file),source_snapshot_sha256=chosen['source_snapshot_sha256'],reason='Inspect genuinely observed unresolved root link; no descendant claim until content evidence'))
    atomic_json(output/'coverage-plan.json',plan)
    print(json.dumps(summary));print(json.dumps(dict(selected_tests=plan)))


if __name__=='__main__':reconcile()
