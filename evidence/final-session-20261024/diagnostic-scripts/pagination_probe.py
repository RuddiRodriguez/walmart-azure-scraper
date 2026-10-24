import json,signal,time,hashlib
from pathlib import Path
from browser import open_browser,select_store,navigate,verify_banner
from extract import next_data
from storage import atomic_json
from bs4 import BeautifulSoup
from datetime import datetime,timezone
out=Path('data/final-session-20261024/pagination-native');out.mkdir()
settings=json.loads(Path('config/stores.json').read_text());settings.update(retries=1,max_page_seconds=30)
store=settings['stores'][0]
result={'mode':'live two-parent pagination diagnostic; no product collection or publication','observations':[]}
def log(event,**values):
 with (out/'events.jsonl').open('a') as f:f.write(json.dumps({'time':datetime.now(timezone.utc).isoformat(),'event':event,**values})+'\n')
def inspect(stage):
 html=sb.get_page_source();(out/(stage+'.html')).write_text(html)
 soup=BeautifulSoup(html,'html.parser');verify_banner(soup,store)
 search=next_data(soup).get('searchResult') or {};pagination=search.get('paginationV2') or {};props=pagination.get('pageProperties') or {}
 node=soup.select_one('a[aria-current="page"]');link=soup.select_one('a[aria-label="Next Page"]')
 row={'stage':stage,'url':sb.get_current_url(),'source_sha256':hashlib.sha256(html.encode()).hexdigest(),'structured_page':props.get('page'),'structured_max_page':pagination.get('maxPage'),'structured_stores':props.get('stores'),'structured_facet':props.get('facet'),'visible_page':node.get_text(' ',strip=True) if node else '', 'next_href':link.get('href') if link else None,'product_ids':[str(x.get('usItemId')) for stack in search.get('itemStacks',[]) for x in stack.get('items',[]) if x.get('__typename')=='Product']}
 soup.clear(decompose=True);soup.decompose();result['observations'].append(row);atomic_json(out/'results.json',result);print(json.dumps(row),flush=True)
def timeout(*_):raise TimeoutError('180 second pagination budget reached')
signal.signal(signal.SIGALRM,timeout);signal.alarm(180)
sb=None;started=time.monotonic()
try:
 sb=open_browser();select_store(sb,store,settings,log,out)
 for name,url in [('food','https://www.walmart.com/cp/food/976759'),('diapering','https://www.walmart.com/browse/diapering/5427_486190')]:
  soup=navigate(sb,url,settings,log);soup.clear(decompose=True);soup.decompose();inspect(name+'_before')
  sb.click('a[aria-label="Next Page"]');sb.sleep(4);inspect(name+'_clicked')
  actual=sb.get_current_url()
  if actual.split('#')[0] != url:
   soup=navigate(sb,actual,settings,log);soup.clear(decompose=True);soup.decompose();inspect(name+'_reloaded')
 result['completed']=True
except Exception as error:result.update(error=str(error),error_type=type(error).__name__);print(json.dumps({'error':str(error)}),flush=True)
finally:
 signal.alarm(0);result['seconds']=round(time.monotonic()-started,2);atomic_json(out/'results.json',result)
 if sb:sb.quit()
