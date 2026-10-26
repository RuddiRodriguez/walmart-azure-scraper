"""Offline queue growth and repeated listing audit; no retailer requests."""
import hashlib,json,re,sqlite3
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from extract import category_id
from storage import atomic_json


def listing_ids(search):
    return sorted({str(i['usItemId']) for stack in search.get('itemStacks',[]) for i in stack.get('items',[]) if i.get('__typename')=='Product' and i.get('usItemId') and not i.get('isSponsoredFlag') and not i.get('sponsoredProduct')})


def audit():
 root=Path('data/full-coverage-20261026');out=Path('evidence/queue-growth-audit-20261026');out.mkdir(exist_ok=True)
 c=sqlite3.connect(root/'queue.sqlite');rows=c.execute('SELECT category,key,url,status,scope_review FROM pages').fetchall();counts=Counter();page_numbers=[]
 for cat,key,url,status,review in rows:
  page=int((parse_qs(urlsplit(url).query).get('page') or ['1'])[0]);page_numbers.append(page)
  counts['pagination' if page>1 else 'category_first_page']+=1
  if status=='pending':counts['pending_pagination' if page>1 else 'pending_first_page']+=1
 keys=[(r[0],r[1]) for r in rows]
 fingerprints=defaultdict(list);batches=[];bodies=0
 for batch in sorted(root.glob('batch-*')):
  if not (batch/'report.json').exists():continue
  report=json.loads((batch/'report.json').read_text());by_url={p['url']:p for p in report['pages']};by_sequence={p.get('listing_sequence'):p for p in report['pages'] if p.get('listing_sequence')}
  batches.append(dict(batch=batch.name,queue_counts=report.get('queue_counts'),pages_attempted=len(report['pages'])))
  for path in (batch/'captures').glob('*.json'):
   meta=json.loads(path.read_text())
   if meta['kind']!='listing' or not meta.get('body_file'):continue
   entry=by_sequence.get(meta['sequence']) or by_url.get(meta['request']['url'])
   if not entry or entry.get('status')!='reviewed':continue
   body=(path.parent/meta['body_file']).read_bytes();assert hashlib.sha256(body).hexdigest()==meta['body_sha256'];bodies+=1
   match=re.search(rb'<script\b(?=[^>]*\bid=[\"\x27]__NEXT_DATA__[\"\x27])[^>]*>(.*?)</script\s*>',body,re.S)
   if not match:continue
   search=json.loads(match.group(1))['props']['pageProps'].get('initialData',{}).get('searchResult')
   if not search:continue
   ids=listing_ids(search)
   if not ids:continue
   actual=str((search.get('catInfo') or {}).get('catId') or '')
   page=int(((search.get('paginationV2') or {}).get('pageProperties') or {}).get('page') or 1)
   digest=hashlib.sha256(json.dumps(ids).encode()).hexdigest()
   fingerprints[(entry['category'],actual.split('_')[-1],digest)].append(dict(page=page,body_sha256=meta['body_sha256'],capture=str(path),product_count=len(ids)))
 repeats=[dict(category=k[0],category_id=k[1],listing_ids_sha256=k[2],observations=v) for k,v in fingerprints.items() if len({e['page'] for e in v})>1]
 summary=dict(mode='Offline audit of stored real coverage responses and queue',queue_counts=dict(Counter(r[3] for r in rows)),page_identity_duplicates=len(keys)-len(set(keys)),url_types=dict(counts),page_number_range=[min(page_numbers),max(page_numbers)],captured_listing_bodies_hash_verified=bodies,repeated_product_sets_across_different_pages=len(repeats),batch_progress=batches,full_coverage_complete=False,live_requests=0)
 atomic_json(out/'summary.json',summary);atomic_json(out/'repeated-listings.json',repeats)
 cache=[dict(category=k[0],leaf=k[1],fingerprint=k[2],page=e['page'],source=e['capture'],body_sha256=e['body_sha256']) for k,values in fingerprints.items() for e in values]
 atomic_json(root/'historical-fingerprints.json',cache)
 print(json.dumps({k:v for k,v in summary.items() if k!='batch_progress'}))


if __name__=='__main__':audit()
