"""Offline trace and retention replay for every requested rejection in two existing live runs."""
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup
from capture_store_drift import listing_from_rendered
from extract import next_data, product_record
from trace_store_context import product_context
from storage import atomic_json
import retention

RUNS=['controlled-skip-invalid-20261025','controlled-skip-invalid-repeat-20261025']


def audit():
    output=Path('evidence/retention-step2-20261026');output.mkdir(exist_ok=True)
    private=Path('data/retention-step2-20261026');private.mkdir(exist_ok=True)
    dbpath=private/'catalog.sqlite'
    if dbpath.exists():
        raise ValueError('Replay output already exists; keep evidence, use a fresh folder for another attempt')
    settings=json.loads(Path('config/stores.json').read_text());store=settings['stores'][0]
    db=retention.connect(dbpath,store);events=[];traces=[];original_hashes={}
    for name in RUNS:
        run=Path('data')/name;public=Path('evidence')/name
        report=json.loads((run/'report.json').read_text());rows=json.loads((public/'products.json').read_text())
        original_hashes[str(public/'products.json')]=hashlib.sha256((public/'products.json').read_bytes()).hexdigest()
        by_url={r['url']:r for r in rows}
        for source in json.loads((run/'source-records.json').read_text()):
            row=by_url[source['candidate']['url']]
            assert str(source['product']['usItemId'])==source['candidate']['item_id']
            assert product_context(source['product'],store)['store_matches']
            events.append(dict(kind='previously_accepted',date=row['crawl_date'],row=row,source=source,name=name))
        cache={}
        for rejected in json.loads((public/'rejected-responses.json').read_text()):
            if rejected['reason'] not in ['no_local_pickup','price_changed']:continue
            seq=rejected['listing_sequence']
            if seq not in cache:
                page_entry=next(e for e in report['pages'] if e.get('listing_sequence')==seq)
                snapshot=run/page_entry['snapshot']
                assert hashlib.sha256(snapshot.read_bytes()).hexdigest()==page_entry['snapshot_sha256']
                meta=json.loads((run/'captures'/f'collection-{seq:03}.json').read_text());body=run/'captures'/meta['body_file']
                assert hashlib.sha256(body.read_bytes()).hexdigest()==meta['body_sha256']
                page=BeautifulSoup(body.read_bytes(),'html.parser')
                candidates,_,_=listing_from_rendered(snapshot,page,page_entry['category'],store)
                cache[seq]={c['item_id']:c for c in candidates}
            key=rejected['expected_product_id'];candidate=cache[seq][key]
            meta_path=run/'captures'/f"collection-{rejected['sequence']:03}.json"
            meta=json.loads(meta_path.read_text());body=run/'captures'/meta['body_file']
            assert hashlib.sha256(body.read_bytes()).hexdigest()==meta['body_sha256']==rejected['body_sha256']
            assert all(r['url']!=candidate['url'] for r in rows)
            events.append(dict(kind='previously_rejected',date=meta['response']['received_utc'],candidate=candidate,
                               body=body,meta=meta,rejected=rejected,name=name,source_commit=report['source_commit']))
    for e in sorted(events,key=lambda e:e['date']):
        if e['kind']=='previously_accepted':
            source=e['source'];key=source['candidate']['item_id'];known=retention.known_assortment(db,key)
            state=retention.product_state(source['candidate'],source['product'],store,known)
            retention.observe(db,key,e['row'],state,e['name']+'#'+str(source['product_sequence']),e['date'],True)
            continue
        candidate=e['candidate'];key=candidate['item_id'];known=retention.known_assortment(db,key)
        soup=BeautifulSoup(e['body'].read_bytes(),'html.parser');product=next_data(soup)['data']['product']
        context=product_context(product,store);assert context['store_matches']
        row,reason,_=product_record(candidate,soup,store,settings['private_labels'],'',retain_missing=True,known_store_assortment=known)
        assert row is not None or reason=='marketplace', (key,reason)
        assert not row or all(row[k]=='' for k in retention.PRICE_FIELDS), (key,reason)
        state=retention.product_state(candidate,product,store,known,reason) if row else 'excluded_marketplace'
        row=retention.observe(db,key,row,state,e['name']+'#'+str(e['rejected']['sequence']),e['date'],bool(row and state!='assortment_unverified'))
        traces.append(dict(run=e['name'],capture_source_commit=e['source_commit'],product_id=key,
            old_reason=e['rejected']['reason'],old_outcome='Absent from that original506export; original file unchanged',
            observed_utc=e['date'],listing_sequence=e['rejected']['listing_sequence'],product_sequence=e['rejected']['sequence'],
            body_sha256=e['meta']['body_sha256'],listing_price_text=candidate['price_text'],
            listing_pickup_at_store=candidate['local_pickup_at_listing'],
            product_availability=product.get('availabilityStatus'),
            pickup_options=[{k:o[k] for k in ['type','intent','availabilityStatus','locationText'] if k in o} for o in product.get('fulfillmentOptions') or [] if o.get('type')=='PICKUP'],
            new_reason=reason,new_state=state,assortment_confirmed=bool(row and state!='assortment_unverified'),
            listing_seller=candidate['item'].get('sellerName'),product_seller=product.get('sellerName') or product.get('sellerDisplayName'),
            repaired_historical_row=row,source_fields_verified=True,**{k:v for k,v in context.items() if k!='product_id'}))
    summary=retention.export(db,output);db.close()
    for name,digest in original_hashes.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    summary.update(replay_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                   replay_source_hashes={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in ['retention.py','extract.py','tools/audit_rejected_retention.py','validate.py']},mode='Offline replay/repair of existing captured live observations, NOT new live collection or merged fresh500claim',
                   traced_rejection_events=len(traces),distinct_traced_products=len({t['product_id'] for t in traces}),
                   old_reasons=dict(Counter(t['old_reason'] for t in traces)),new_states=dict(Counter(t['new_state'] for t in traces)),
                   every_requested_rejection_accounted_for=True,eligible_products_retained=True,noneligible_marketplace_exclusions_documented=True,all_unsupported_current_prices_blank=True,
                   observation_dates_from_original_sources=True,original_datasets_unchanged=original_hashes,
                   unavailability_vs_missing_evidence_distinguished=True,live_requests=0,client_sent=False)
    atomic_json(output/'rejection-trace.json',traces);atomic_json(output/'summary.json',summary)
    print(json.dumps(summary))


if __name__=='__main__':audit()
