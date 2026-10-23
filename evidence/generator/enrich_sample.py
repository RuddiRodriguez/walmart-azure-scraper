import asyncio
import json
import time
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from seleniumbase import sb_cdp

p=Path(__file__).parent/'sample'
out=p/'details'; out.mkdir(exist_ok=True)
rows=json.loads((p/'products.json').read_text())
evidence=json.loads((p/'evidence.json').read_text())
queue=[]
groups={r['category']:[] for r in rows}
for r,e in zip(rows,evidence): groups[r['category']].append((r,e))
while any(groups.values()):
    for group in groups.values():
        if group: queue.append(group.pop(0))
accepted=[]; proofs=[]; rejected=[]
if (out/'products.json').exists():
    accepted=json.loads((out/'products.json').read_text()); proofs=json.loads((out/'proofs.json').read_text()); rejected=json.loads((out/'rejected.json').read_text())
done={x['item_id'] for x in proofs+rejected}


def save():
    for name,obj in [('products',accepted),('proofs',proofs),('rejected',rejected)]:
        (out/(name+'.json')).write_text(json.dumps(obj,indent=2,ensure_ascii=False))


sb=sb_cdp.Chrome(locale='en',guest=True)
try:
    sb.goto('https://www.walmart.com/'); sb.sleep(4)
    sb.click('[data-automation-id="fulfillment-banner"]'); sb.click('button:contains("8915 GERBER ROAD")'); sb.sleep(2)
    sb.type('#zip-code-or-city-state','72712'); sb.press_keys('#zip-code-or-city-state','\n'); sb.sleep(3)
    sb.click('input[id^="100-"]'); sb.click('button:contains("Save")'); sb.sleep(4)
    if not sb.is_element_visible('#intent-id1'): sb.click('[data-automation-id="fulfillment-banner"]')
    sb.click('#intent-id1'); sb.sleep(3)
    for row,ev in queue:
        key=ev['item_id']
        if key in done: continue
        expression='fetch('+json.dumps(row['url'])+').then(async r => ({status:r.status, url:r.url, html:await r.text()}))'
        response=sb.loop.run_until_complete(asyncio.wait_for(sb.page.evaluate(expression,await_promise=True),timeout=45))
        soup=BeautifulSoup(response['html'],'html.parser')
        title=soup.title.get_text() if soup.title else ''
        if response['status']!=200 or 'robot or human' in title.lower():
            (out/'blocked.html').write_text(response['html']); raise RuntimeError('Detail access blocked: '+str(response['status'])+' '+title)
        node=soup.select_one('#__NEXT_DATA__')
        product=json.loads(node.string).get('props',{}).get('pageProps',{}).get('initialData',{}).get('data',{}).get('product',{}) if node else {}
        (out/(key+'.json')).write_text(json.dumps(product,indent=2))
        reason=''
        loc=product.get('location') or {}
        summary=product.get('fulfillmentSummary') or []
        price=product.get('priceInfo') or {}
        current=(price.get('currentPrice') or {}).get('price')
        promos=[x for x in (product.get('promoData') or []) if x.get('type') not in ['1PAYCC','AFFIRM','ONEPAY','CREDIT_CARD']]
        if str(product.get('usItemId'))!=key: reason='product_id_mismatch'
        elif loc.get('intent')!='PICKUP' or str((loc.get('pickupLocation') or {}).get('storeId'))!='100': reason='location_mismatch'
        elif not any(x.get('fulfillment')=='PICKUP' and str(x.get('storeId'))=='100' for x in summary): reason='no_pickup100'
        elif (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart.com','Walmart']: reason='seller_changed'
        elif current is None or f'{current:.2f}'!=(row['sale_price'] or row['regular_price']): reason='price_changed_or_missing'
        elif promos or product.get('promoDiscount') or price.get('volumePriceTiers'): reason='promotion_needs_review'
        if reason:
            rejected.append({'item_id':key,'reason':reason,'category':row['category']})
        else:
            row['upc']=str(product.get('upc') or '')
            brand=product.get('brand') or ''
            if brand in ['Great Value','Equate',"Parent's Choice",'Special Kitty',"Ol’ Roy",'Pen+Gear','bettergoods','Mainstays']: row['store_brand']=brand
            accepted.append(row)
            proofs.append({'item_id':key,'category':row['category'],'detail_file':key+'.json','listing_file':ev['source'],'location':loc,'upc_available':bool(row['upc']),'listing_seller':ev['seller'],'detail_seller':product.get('sellerName'),'current_price':current})
        done.add(key)
        save()
        if len(done)%10==0: print('checked',len(done),'accepted',len(accepted),'rejected',dict(Counter(r['reason'] for r in rejected)),flush=True)
        if len(accepted)>=500 and len({r['category'] for r in accepted})==11: break
        time.sleep(1)
except Exception as exc:
    (out/'error.txt').write_text(str(exc)); print('STOP',exc,flush=True); raise
finally:
    save(); sb.quit()
