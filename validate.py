import re
from collections import Counter
from datetime import datetime
from urllib.parse import urlsplit
from extract import FIELDS, APPROX


def validate(rows, categories, store, settings, pending_pages, pending_products, review_count, previous=None, unavailable_urls=()):
    errors = []
    counts = Counter(row.get('category', '') for row in rows if isinstance(row, dict) and isinstance(row.get('category', ''), str))
    urls = [r.get('url', '') for r in rows if isinstance(r, dict) and isinstance(r.get('url', ''), str)]
    ids = [urlsplit(url).path.rstrip('/').split('/')[-1] for url in urls]
    if len(rows) < settings['minimum_records']:
        errors.append('Below minimum product count')
    for category in categories:
        if counts[category] < settings['minimum_category_records']:
            errors.append('Missing or thin category: ' + category)
    if pending_pages or pending_products:
        errors.append('Incomplete checkpoint queue')
    if review_count:
        errors.append('Unresolved product prices, availability or promotions require review')
    if len(set(urls)) != len(urls):
        errors.append('Duplicate product URLs')
    if len(set(ids)) != len(ids):
        errors.append('Duplicate product IDs')
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or list(row) != FIELDS or not all(isinstance(v, str) for v in row.values()):
            errors.append(f'Record {index}: schema')
            continue
        if row['gupc'] or row['unit_price'] or APPROX.search(row['weight']):
            errors.append(f'Record {index}: forbidden field value')
        if row['zipcode'] != store['zip'] or row['store_name'] != store['name'] or row['store_location'] != store['address']:
            errors.append(f'Record {index}: store')
        if row['category'] not in categories:
            errors.append(f'Record {index}: unknown category')
        required = ['product_title', 'url', 'image_url', 'category', 'crawl_date']
        if row['url'] not in unavailable_urls:
            required.append('regular_price')
        for field in required:
            if not row[field]:
                errors.append(f'Record {index}: missing {field}')
        parts = urlsplit(row['url'])
        if parts.scheme != 'https' or parts.netloc != 'www.walmart.com' or not re.fullmatch(r'/ip/(?:[^/]+/)?\d+', parts.path.rstrip('/')):
            errors.append(f'Record {index}: product URL')
        try:
            if datetime.fromisoformat(row['crawl_date']).tzinfo is None:
                raise ValueError('Missing timezone')
        except ValueError:
            errors.append(f'Record {index}: crawl date')
        for field in ['regular_price', 'sale_price', 'volume_deals_price', 'digital_deals_price']:
            if row[field] and not re.fullmatch(r'\d+\.\d{2}', row[field]):
                errors.append(f'Record {index}: invalid {field}')
    if previous:
        for category, previous_count in previous.get('category_counts', {}).items():
            if counts[category] < previous_count * settings['minimum_yield_ratio']:
                errors.append('Material yield decline: ' + category)
    return {'passed': not errors, 'records': len(rows), 'errors': errors,
            'category_counts': dict(counts), 'duplicate_urls': len(urls) - len(set(urls)),
            'duplicate_product_ids': len(ids) - len(set(ids)),
            'field_nonempty_counts': {f: sum(bool(r.get(f)) for r in rows if isinstance(r, dict)) for f in FIELDS},
            'pending_pages': pending_pages, 'pending_products': pending_products,
            'products_needing_review': review_count,
            'retained_unavailable_records': sum(url in unavailable_urls for url in urls)}
