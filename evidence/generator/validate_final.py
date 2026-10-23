import json
import re
from collections import Counter
from pathlib import Path

p = Path(__file__).parent / 'sample'
fields = 'zipcode store_name store_location store_logo store_brand category sub_category product_title weight regular_price sale_price volume_deals_description volume_deals_price digital_deals_description digital_deals_price image_url url upc gupc ppm unit_price crawl_date'.split()
rows = json.loads((p / 'details/products.json').read_text())
proofs = json.loads((p / 'details/proofs.json').read_text())
evidence = {e['item_id']: e for e in json.loads((p / 'evidence.json').read_text())}
errors = []
for index, (row, proof) in enumerate(zip(rows, proofs)):
    item_id = proof['item_id']
    ev = evidence[item_id]
    product = json.loads((p / 'details' / proof['detail_file']).read_text())
    ppm = re.search(r'(?:\$\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*¢)\s*/\s*(?:\d+\s*)?(?:fl\s*oz|ounces?|oz|lbs?|count|ct|each|ea|qt|gal|sq\s*ft|ft|ml|kg|g|l)\b', ev['displayed_price'], re.I)
    if ppm:
        row['ppm'] = ppm.group()
    failures = []
    term = {'Health & Wellness': 'health and medicine', 'Balloons': 'balloon'}.get(row['category'], row['category'].lower())
    if term not in (ev['source_item'].get('category') or {}).get('categoryPath', '').lower():
        failures.append('category_scope')
    if list(row) != fields or not all(isinstance(v, str) for v in row.values()):
        failures.append('schema')
    if row['gupc'] or row['unit_price']:
        failures.append('downstream_fields')
    if row['zipcode'] != '72712' or row['store_name'] != 'Bentonville S Walton Blvd Supercenter':
        failures.append('store')
    location = product.get('location') or {}
    if location.get('intent') != 'PICKUP' or str((location.get('pickupLocation') or {}).get('storeId')) != '100':
        failures.append('detail_location')
    for label, summary in [('listing', ev['pickup']), ('detail', product.get('fulfillmentSummary') or [])]:
        if not any(x.get('fulfillment') == 'PICKUP' and str(x.get('storeId')) == '100' for x in summary):
            failures.append(label + '_pickup')
    if ev['seller'] != 'Walmart.com' or (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart', 'Walmart.com']:
        failures.append('seller')
    if ev['source_item'].get('isSponsoredFlag') or ev['source_item'].get('sponsoredProduct') or 'Sponsored' in ev['card_text']:
        failures.append('sponsored')
    if row['ppm'] and row['ppm'] not in ev['displayed_price']:
        failures.append('ppm_not_verbatim')
    if row['upc'] != str(product.get('upc') or ''):
        failures.append('upc_changed')
    if str(product.get('usItemId')) != item_id:
        failures.append('product_id')
    current = (product.get('priceInfo', {}).get('currentPrice') or {}).get('price')
    if current is None or f'{current:.2f}' != (row['sale_price'] or row['regular_price']):
        failures.append('price')
    if re.search(r'\bapprox(?:imately)?\b', row['weight'], re.I):
        failures.append('approx_weight')
    for field in ['regular_price', 'sale_price', 'volume_deals_price', 'digital_deals_price']:
        if row[field] and not re.fullmatch(r'\d+\.\d{2}', row[field]):
            failures.append(field + '_format')
    for field in ['product_title', 'regular_price', 'image_url', 'url', 'category', 'crawl_date']:
        if not row[field]:
            failures.append(field + '_missing')
    if failures:
        errors.append({'index': index, 'item_id': item_id, 'errors': failures})
ids = [x['item_id'] for x in proofs]
report = {
    'records': len(rows),
    'proof_count': len(proofs),
    'duplicate_ids': len(ids) - len(set(ids)),
    'duplicate_urls': len(rows) - len({r['url'] for r in rows}),
    'errors': errors,
    'category_counts': dict(Counter(r['category'] for r in rows)),
    'field_nonempty_counts': {f: sum(bool(r[f]) for r in rows) for f in fields},
    'detail_rejections': dict(Counter(r['reason'] for r in json.loads((p / 'details/rejected.json').read_text()))),
}
report['passed'] = len(rows) >= 500 and len(proofs) == len(rows) and len(report['category_counts']) == 11 and not errors and not report['duplicate_ids'] and not report['duplicate_urls']
(p / 'final_validation.json').write_text(json.dumps(report, indent=2))
if report['passed']:
    (p / 'validated_500_products.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False))
print(json.dumps(report, indent=2))
