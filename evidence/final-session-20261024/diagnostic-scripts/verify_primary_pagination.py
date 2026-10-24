import json,signal,time,hashlib
from pathlib import Path
from browser import open_browser,select_store,navigate,verify_banner
from extract import next_data
from scrape import next_page_url,verify_listing_store
from storage import atomic_json
from datetime import datetime,timezone
out=Path('data/final-session-20261024/primary-pagination-live');out.mkdir()
settings=json.loads(Path('config/stores.json').read_text());settings.update(retries=1,max_page_seconds=30);store=settings['stores'][0]
result={'mode':'live two-page primary-listing verification; not product/detail or full catalog acceptance','pages':[]}
def log(event,**values):
 with (out/'events.jsonl').open('a') as f:f.write(json.dumps({'time':datetime.now(timezone.utc).isoformat(),'event':event,**values})+'\n')
def timeout(*_):raise TimeoutError('180 second primary-pagination limit')
signal.signal(signal.SIGALRM,timeout);signal.alarm(180);sb=None;started=time.monotonic()
try:
 sb=open_browser();select_store(sb,store,settings,log,out)
 url='https://www.walmart.com/browse/diapering/5427_486190'
 for page in [1,2]:
  soup=navigate(sb,url,settings,log);verify_banner(soup,store);search=next_data(soup)['searchResult'];verify_listing_store(search,store)
  assert int(search['paginationV2']['pageProperties']['page'])==page
  html=str(soup);(out/(str(page)+'.html')).write_text(html)
  ids=[str(x.get('usItemId')) for s in search.get('itemStacks',[]) for x in s.get('items',[]) if x.get('__typename')=='Product']
  result['pages'].append({'page':page,'url':sb.get_current_url(),'source_sha256':hashlib.sha256(html.encode()).hexdigest(),'stores':search['paginationV2']['pageProperties'].get('stores'),'facet':search['paginationV2']['pageProperties'].get('facet'),'product_ids':ids})
  url=next_page_url(soup,sb.get_current_url(),search);soup.clear(decompose=True);soup.decompose()
 assert set(result['pages'][1]['product_ids'])-set(result['pages'][0]['product_ids'])
 result['new_ids_on_page_two']=len(set(result['pages'][1]['product_ids'])-set(result['pages'][0]['product_ids']));result['passed']=True
except Exception as error:result.update(passed=False,error=str(error),error_type=type(error).__name__)
finally:
 signal.alarm(0);result['seconds']=round(time.monotonic()-started,2);atomic_json(out/'results.json',result)
 if sb:sb.quit()
print(json.dumps(result),flush=True)
raise SystemExit(0 if result['passed'] else 1)
