import json
import re
from collections import Counter
from pathlib import Path

p=Path(__file__).parent/'sample'
fields='zipcode store_name store_location store_logo store_brand category sub_category product_title weight regular_price sale_price volume_deals_description volume_deals_price digital_deals_description digital_deals_price image_url url upc gupc ppm unit_price crawl_date'.split()
rows=json.loads((p/'products.json').read_text())
evidence=json.loads((p/'evidence.json').read_text())
errors=[]
for index,(r,e) in enumerate(zip(rows,evidence)):
    failures=[]
    if list(r)!=fields: failures.append('field_order')
    if not all(isinstance(v,str) for v in r.values()): failures.append('non_string')
    if r['gupc'] or r['unit_price']: failures.append('downstream_fields_not_blank')
    if r['zipcode']!='72712' or r['store_name']!='Bentonville S Walton Blvd Supercenter': failures.append('location')
    if e['seller']!='Walmart.com' or not any(str(x.get('storeId'))=='100' and x.get('fulfillment')=='PICKUP' for x in e['pickup']): failures.append('seller_or_pickup')
    if e['source_item'].get('isSponsoredFlag') or e['source_item'].get('sponsoredProduct') or 'Sponsored' in e['card_text']: failures.append('sponsored')
    if r['ppm'] and r['ppm'] not in e['displayed_price']: failures.append('ppm_not_verbatim')
    if re.search(r'\bapprox|approximately',r['weight'],re.I): failures.append('approx_weight')
    for f in ['regular_price','sale_price','volume_deals_price','digital_deals_price']:
        if r[f] and not re.fullmatch(r'\d+\.\d{2}',r[f]): failures.append(f+'_format')
    for f in ['product_title','regular_price','image_url','url','category','crawl_date']:
        if not r[f]: failures.append(f+'_missing')
    if failures: errors.append({'index':index,'errors':failures})
ids=[e['item_id'] for e in evidence]
report={'records':len(rows),'duplicate_ids':len(ids)-len(set(ids)),'errors':errors,'category_counts':dict(Counter(r['category'] for r in rows)),'field_nonempty_counts':{f:sum(bool(r[f]) for r in rows) for f in fields},'limits':['Listing-level extraction. UPC not exposed in listing data; product-page enrichment not yet performed.','Promotions requiring detail review excluded, not classified as absent.','All-category sampling does not prove full subcategory/catalog coverage.','Local run only; Azure not tested.']}
(p/'validation.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
