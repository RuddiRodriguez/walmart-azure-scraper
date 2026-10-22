import re
from collections import Counter
from extract import FIELDS, APPROX


def validate(rows, categories, store, settings, pending_pages, pending_products, review_count, previous=None):
    errors = []
    counts = Counter(row['category'] for row in rows)
    if len(rows) < settings['minimum_records']:
        errors.append('Below minimum product count')
    for category in categories:
        if counts[category] < settings['minimum_category_records']:
            errors.append('Missing or thin category: ' + category)
    if pending_pages or pending_products:
        errors.append('Incomplete checkpoint queue')
    if review_count:
        errors.append('Unrecognized promotions require review before full publication')
    if len({row['url'] for row in rows}) != len(rows):
        errors.append('Duplicate product URLs')
    for index, row in enumerate(rows):
        if list(row) != FIELDS or not all(isinstance(v, str) for v in row.values()):
            errors.append(f'Record {index}: schema')
        if row.get('gupc') or row.get('unit_price') or APPROX.search(row.get('weight', '')):
            errors.append(f'Record {index}: forbidden field value')
        if row.get('zipcode') != store['zip'] or row.get('store_name') != store['name']:
            errors.append(f'Record {index}: store')
        for field in ['product_title', 'regular_price', 'url', 'image_url', 'category', 'crawl_date']:
            if not row.get(field):
                errors.append(f'Record {index}: missing {field}')
        for field in ['regular_price', 'sale_price', 'volume_deals_price', 'digital_deals_price']:
            if row.get(field) and not re.fullmatch(r'\d+\.\d{2}', row[field]):
                errors.append(f'Record {index}: invalid {field}')
    if previous:
        for category, previous_count in previous.get('category_counts', {}).items():
            if counts[category] < previous_count * settings['minimum_yield_ratio']:
                errors.append('Material yield decline: ' + category)
    return {'passed': not errors, 'records': len(rows), 'errors': errors,
            'category_counts': dict(counts), 'duplicate_urls': len(rows) - len({r['url'] for r in rows}),
            'field_nonempty_counts': {f: sum(bool(r[f]) for r in rows) for f in FIELDS},
            'pending_pages': pending_pages, 'pending_products': pending_products,
            'promotions_needing_review': review_count}
