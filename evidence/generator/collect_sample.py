import csv
import json
import re
import time
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from seleniumbase import sb_cdp

BASE = Path(__file__).parent
OUT = BASE / 'sample'
OUT.mkdir(exist_ok=True)
FIELDS = 'zipcode store_name store_location store_logo store_brand category sub_category product_title weight regular_price sale_price volume_deals_description volume_deals_price digital_deals_description digital_deals_price image_url url upc gupc ppm unit_price crawl_date'.split()
rows, evidence, coverage = [], [], []
seen = set()
rejected = Counter()
started = time.monotonic()
if '--resume' in sys.argv and (OUT/'products.json').exists():
    rows=json.loads((OUT/'products.json').read_text())
    evidence=json.loads((OUT/'evidence.json').read_text())
    prior=json.loads((OUT/'progress.json').read_text())
    coverage=prior['coverage']
    rejected=Counter(prior['rejected'])
    seen={e['item_id'] for e in evidence}
sb = sb_cdp.Chrome(locale='en', guest=True)


def write():
    (OUT/'products.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
    (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False))
    (OUT/'progress.json').write_text(json.dumps({'count':len(rows),'seconds':round(time.monotonic()-started),'rejected':dict(rejected),'coverage':coverage},indent=2))


def read_page(label):
    html = sb.get_page_source()
    soup = BeautifulSoup(html,'html.parser')
    title = soup.title.get_text() if soup.title else ''
    if 'robot or human' in title.lower():
        (OUT/(label+'_blocked.html')).write_text(html)
        raise RuntimeError('Bot challenge: '+label)
    banner = soup.select_one('[data-automation-id="fulfillment-banner"]')
    if not banner or 'Pickup Bentonville S Walton Blvd Supercenter' not in banner.get_text(' ',strip=True):
        raise RuntimeError('Store/pickup mismatch: '+label)
    (OUT/(label+'.html')).write_text(html)
    return soup


def collect(soup, category, label):
    script = soup.select_one('#__NEXT_DATA__')
    data = json.loads(script.string) if script else {}
    result = data.get('props',{}).get('pageProps',{}).get('initialData',{}).get('searchResult',{})
    items = [i for stack in result.get('itemStacks',[]) for i in stack.get('items',[]) if i.get('__typename')=='Product']
    cards = {c.get('data-item-id'):c for c in soup.select('[data-item-id]')}
    added = 0
    for item in items:
        card = cards.get(item.get('id'))
        if not card:
            rejected['not_rendered']+=1; continue
        text = card.get_text(' ',strip=True)
        if item.get('isSponsoredFlag') or item.get('sponsoredProduct') or 'Sponsored' in text:
            rejected['sponsored']+=1; continue
        if item.get('sellerName') != 'Walmart.com':
            rejected['non_walmart_seller']+=1; continue
        pickup = [f for f in (item.get('fulfillmentSummary') or []) if f.get('fulfillment')=='PICKUP' and str(f.get('storeId'))=='100']
        if not pickup or 'Pickup' not in text:
            rejected['no_store100_pickup']+=1; continue
        if item.get('availabilityStatus')!='IN_STOCK':
            rejected['not_in_stock']+=1; continue
        name = item.get('name','')
        price = card.select_one('[data-testid="unified-global-product-price-a11y-text"]')
        price_text = price.get_text(' ',strip=True) if price else ''
        current = re.search(r'(?:Price Now|Price) \$(\d+(?:\.\d{1,2})?)',price_text)
        was = re.search(r'Was \$(\d+(?:\.\d{1,2})?)',price_text)
        if not current or 'From ' in price_text:
            rejected['missing_or_range_price']+=1; continue
        if re.search(r'\b(?:approx\.?|approximately|about)\b',name,re.I) or item.get('priceInfo',{}).get('finalCostByWeight'):
            rejected['approx_or_variable_weight']+=1; continue
        if item.get('promoData') or item.get('promoDiscount') or item.get('rewards') or re.search(r'clip|cash back|cashback|buy \d|save.*when|extra savings|coupon',text,re.I):
            rejected['promotion_needs_detail_review']+=1; continue
        key = item.get('usItemId')
        if key in seen:
            rejected['duplicate']+=1; continue
        link = card.select_one('a[href*="/ip/"]'); img = card.select_one('img[data-testid="productTileImage"]')
        if not link or not img or not name:
            rejected['missing_core_field']+=1; continue
        ppm_match = re.search(r'(?:\$\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*¢)\s*/\s*(?:fl\s*oz|oz|lb|ct|ea|qt|gal|ml|kg|g|l)\b',price_text,re.I)
        weight = re.search(r'\b\d+(?:\.\d+)?\s*(?:fl\.?\s*oz|oz|ounces?|lbs?|pounds?|kg|grams?|ml|liters?)\b',name,re.I)
        path = (item.get('category') or {}).get('categoryPath','').split('/')
        row = dict.fromkeys(FIELDS,'')
        row.update(zipcode='72712',store_name='Bentonville S Walton Blvd Supercenter',store_location='406 S WALTON BLVD, Bentonville, AR 72712',store_brand='no',category=category,sub_category=path[-1] if path else '',product_title=name,weight=weight.group() if weight else '',regular_price=f'{float(was.group(1) if was else current.group(1)):.2f}',sale_price=f'{float(current.group(1)):.2f}' if was else '',image_url=img['src'],url=urljoin('https://www.walmart.com',link['href']),upc=str(item.get('upc') or ''),ppm=ppm_match.group() if ppm_match else '',crawl_date=datetime.now(timezone.utc).isoformat())
        # Only identify private labels explicitly named in the product title.
        for brand in ['Great Value','Equate','Parent\'s Choice','Special Kitty','Ol\' Roy','Pen+Gear','bettergoods','Mainstays']:
            if name.lower().startswith(brand.lower()): row['store_brand']=brand; break
        logo = soup.select_one('a[aria-label="Walmart Homepage"] img')
        if logo: row['store_logo']=logo.get('src','')
        rows.append(row); seen.add(key); added+=1
        evidence.append({'item_id':key,'source':label+'.html','seller':item['sellerName'],'pickup':pickup,'displayed_price':price_text,'card_text':text,'source_item':item})
    return len(items), added


try:
    sb.goto('https://www.walmart.com/'); sb.sleep(4)
    sb.click('[data-automation-id="fulfillment-banner"]')
    sb.click('button:contains("8915 GERBER ROAD")'); sb.sleep(2)
    sb.type('#zip-code-or-city-state','72712'); sb.press_keys('#zip-code-or-city-state','\n'); sb.sleep(3)
    sb.click('input[id^="100-"]'); sb.click('button:contains("Save")'); sb.sleep(4)
    if not sb.is_element_visible('#intent-id1'): sb.click('[data-automation-id="fulfillment-banner"]')
    sb.click('#intent-id1'); sb.sleep(3)
    read_page('selected_store'); sb.save_screenshot(str(OUT/'selected_store.png'))
    configs = list(csv.DictReader((BASE/'Walmart_Category_URLs.csv').open()))
    for index, config in enumerate(configs):
        category=config['Category (Auto)']; before=len(rows)
        if '--resume' in sys.argv and sum(r['category']==category for r in rows)>=60: continue
        stats={'category':category,'configured_url':config['URL'],'pages':[],'discovered_subcategories':[],'status':'running'}
        coverage.append(stats)
        sb.goto(config['URL']); sb.sleep(3)
        root=read_page(f'{index:02d}_root')
        if not root.select('a[href*="/browse/"]'):
            sb.sleep(8)
            root=read_page(f'{index:02d}_root')
        links=[]
        if '/browse/' in config['URL']: links.append((category,config['URL']))
        for a in root.select('a[href*="/browse/"]'):
            name=a.get_text(' ',strip=True); url=urljoin('https://www.walmart.com',a['href'])
            if not name or re.search(r'recipes|farm animals|shop all foods?$',name,re.I): continue
            if re.search(r'/0(?:/0)?/?(?:\?|$)',url): continue
            if urlsplit(url).netloc!='www.walmart.com': continue
            clean=url.split('?')[0]
            if clean not in [x[1].split('?')[0] for x in links]: links.append((name,url))
        stats['discovered_subcategories']=[{'name':n,'url':u} for n,u in links]
        # Feasibility sample: multiple pages where needed; full catalog crawl is not claimed.
        for li,(sub,url) in enumerate(links[:8]):
            if len(rows)-before>=60: break
            if not (li==0 and '/browse/' in config['URL']): sb.goto(url); sb.sleep(3)
            for page in range(1,3):
                label=f'{index:02d}_{li:02d}_p{page}'
                soup=read_page(label)
                raw,added=collect(soup,category,label)
                stats['pages'].append({'url':sb.get_current_url(),'raw_products':raw,'accepted':added,'source':label+'.html'})
                write(); print(category,'page',page,'added',added,'category',len(rows)-before,'total',len(rows),flush=True)
                if len(rows)-before>=60: break
                if not soup.select_one('a[aria-label="Next Page"]'): break
                sb.click('a[aria-label="Next Page"]'); sb.sleep(3)
                sb.goto(sb.get_current_url()); sb.sleep(3)
        stats['accepted']=len(rows)-before
        stats['status']='sampled' if stats['accepted'] else 'zero_valid_sample'
        write()
except Exception as exc:
    (OUT/'error.txt').write_text(str(exc)); print('STOP',str(exc),flush=True); write(); raise
finally:
    sb.quit()
    write()
