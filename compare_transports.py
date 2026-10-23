"""Live diagnostic: compare free clients with the browser-selected guest store. No publication."""
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from curl_cffi import requests
from browser import open_browser, select_store, fetch_product, check_html
from extract import next_data, pickup
from storage import atomic_json
from export_run_evidence import PRODUCT_FIELDS


def compare(output, repeats=3):
    settings = json.loads(Path('config/stores.json').read_text())
    store = settings['stores'][0]
    source = json.loads(Path('evidence/post-cleanup-a/source-records.json').read_text())
    urls = [row['candidate']['url'] for row in source if row['candidate']['category'] in ['Food','Health & Wellness']]
    for label in ['post-cleanup-b','rendered-b']:
        urls.append(json.loads((Path('evidence')/label/'failure.json').read_text())['current_work']['url'])
    urls = list(dict.fromkeys(urls))
    output.mkdir(parents=True, exist_ok=True)
    results = []
    def log(event, **values):
        with (output/'events.jsonl').open('a') as stream:
            stream.write(json.dumps({'time':datetime.now(timezone.utc).isoformat(),'event':event,**values})+'\n')
    for repeat in range(1,repeats+1):
        folder=output/str(repeat);folder.mkdir(exist_ok=True)
        sb=None
        try:
            sb=open_browser();select_store(sb,store,settings,log,folder)
            with sync_playwright() as pw:
                connection=pw.chromium.connect_over_cdp(sb.get_endpoint_url())
                context=connection.contexts[0]
                with requests.Session() as session:
                    for cookie in context.cookies():
                        session.cookies.set(cookie['name'],cookie['value'],domain=cookie['domain'],path=cookie['path'])
                    session.headers['User-Agent']=sb.evaluate('navigator.userAgent')
                    for method in ['browser-fetch','playwright-request','curl-session']:
                        for url in urls:
                            started=time.monotonic()
                            row={'repeat':repeat,'method':method,'url':url,'time':datetime.now(timezone.utc).isoformat()}
                            soup=None
                            try:
                                if method=='browser-fetch':
                                    soup=fetch_product(sb,url,settings,log)
                                else:
                                    response=context.request.get(url,timeout=90000) if method=='playwright-request' else session.get(url,timeout=90)
                                    status=response.status if method=='playwright-request' else response.status_code
                                    if status!=200:raise ValueError('HTTP '+str(status))
                                    html=response.text() if method=='playwright-request' else response.text
                                    soup=check_html(html)
                                    if method=='playwright-request':response.dispose()
                                product=next_data(soup).get('data',{}).get('product') or {}
                                location=product.get('location') or {}
                                row.update(product={key:product.get(key) for key in PRODUCT_FIELDS},
                                           passed=(str(product.get('usItemId'))==url.split('?')[0].split('/')[-1]
                                             and location.get('intent')=='PICKUP' and str((location.get('pickupLocation') or {}).get('storeId'))==str(store['id'])
                                             and str(location.get('postalCode'))==store['zip'] and pickup(product,store)
                                             and (product.get('sellerName') or product.get('sellerDisplayName')) in ['Walmart','Walmart.com']
                                             and bool(((product.get('priceInfo') or {}).get('currentPrice') or {}).get('price'))))
                                if not row['passed']:row['error']='Identity, seller, price or store context mismatch'
                            except Exception as error:
                                row.update(passed=False,error=str(error))
                            finally:
                                if soup is not None:soup.clear(decompose=True);soup.decompose()
                            row['seconds']=round(time.monotonic()-started,2)
                            results.append(row);atomic_json(output/'results.json',results)
                            log('transport_result',repeat=repeat,method=method,passed=row['passed'],error=row.get('error'))
                            if not row['passed']:break
                            time.sleep(settings['delay_seconds'])
                connection.close()
        except Exception as error:
            log('session_failure',repeat=repeat,error=str(error))
            atomic_json(folder/'failure.json',{'error':str(error)})
        finally:
            if sb:sb.quit()
    summary={'mode':'live diagnostic only; not full category or production acceptance','repeats_requested':repeats,'urls_per_method':len(urls),'methods':{}}
    for method in ['browser-fetch','playwright-request','curl-session']:
        rows=[r for r in results if r['method']==method]
        summary['methods'][method]={'responses':len(rows),'passed':sum(r['passed'] for r in rows),'failures':len(rows)-sum(r['passed'] for r in rows),'all_repeats_complete':len(rows)==len(urls)*repeats and all(r['passed'] for r in rows)}
    atomic_json(output/'summary.json',summary)
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    compare(Path('evidence/transport-comparison'))
