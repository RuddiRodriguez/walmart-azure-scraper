"""Retailer response parsing. Values come from source fields, never inferred prices."""
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urljoin, urlsplit, parse_qs

from bs4 import BeautifulSoup

FIELDS = 'zipcode store_name store_location store_logo store_brand category sub_category product_title weight regular_price sale_price volume_deals_description volume_deals_price digital_deals_description digital_deals_price image_url url upc gupc ppm unit_price crawl_date'.split()
PPM = re.compile(r'(?:\$\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*¢)\s*/\s*(?:\d+\s*)?(?:fl\s*oz|ounces?|oz|lbs?|count|ct|each|ea|qt|gal|sq\s*ft|ft|ml|kg|g|l)\b', re.I)
WEIGHT = re.compile(r'\b\d+(?:\.\d+)?\s*(?:fl\.?\s*oz|oz|ounces?|lbs?|pounds?|kg|grams?|ml|liters?)\b', re.I)
APPROX = re.compile(r'\b(?:approx\.?|approximately|about|estimated weight)\b', re.I)
FINANCE = {'1PAYCC', 'AFFIRM', 'ONEPAY', 'CREDIT_CARD', 'ONE_PREQUAL'}


def next_data(soup):
    node = soup.select_one('#__NEXT_DATA__')
    if not node:
        raise ValueError('Missing retailer data: response may be incomplete or blocked')
    return json.loads(node.string)['props']['pageProps'].get('initialData', {})


def scope(category, item):
    path = (item.get('category') or {}).get('categoryPath', '')
    term = {'Health & Wellness': 'health and medicine', 'Balloons': 'balloon'}.get(category, category.lower())
    return term in path.lower() and 'farm animals' not in path.lower()


def money(value):
    return '' if value is None else f'{Decimal(str(value)):.2f}'


def pickup(item, store):
    return any(x.get('fulfillment') == 'PICKUP' and str(x.get('storeId')) == str(store['id']) for x in item.get('fulfillmentSummary') or [])


def listing_candidates(soup, category, store):
    result = next_data(soup).get('searchResult')
    if not result:
        return [], [], None
    cards = {c.get('data-item-id'): c for c in soup.select('[data-item-id]')}
    accepted, rejected = [], []
    for stack in result.get('itemStacks', []):
        for item in stack.get('items', []):
            if item.get('__typename') != 'Product':
                continue
            key = str(item.get('usItemId') or '')
            card = cards.get(item.get('id'))
            reason = ''
            text = card.get_text(' ', strip=True) if card else ''
            if item.get('isSponsoredFlag') or item.get('sponsoredProduct') or 'Sponsored' in text:
                reason = 'sponsored'
            elif not scope(category, item):
                reason = 'outside_category'
            elif item.get('sellerName') != 'Walmart.com':
                reason = 'marketplace'
            elif not pickup(item, store):
                reason = 'no_local_pickup'
            elif item.get('availabilityStatus') != 'IN_STOCK':
                reason = 'unavailable'
            elif not card:
                reason = 'not_rendered'
            elif APPROX.search(item.get('name', '')) or (item.get('priceInfo') or {}).get('finalCostByWeight'):
                reason = 'approximate_weight'
            if reason:
                rejected.append({'item_id': key, 'reason': reason})
                continue
            link = card.select_one('a[href*="/ip/"]')
            image = card.select_one('img[data-testid="productTileImage"]')
            price = card.select_one('[data-testid="unified-global-product-price-a11y-text"]')
            if not key.isdigit() or not link or not image or not price:
                rejected.append({'item_id': key, 'reason': 'missing_listing_fields'})
                continue
            product_url = urljoin('https://www.walmart.com', link['href'])
            if urlsplit(product_url).netloc != 'www.walmart.com' or not urlsplit(product_url).path.startswith('/ip/'):
                rejected.append({'item_id': key, 'reason': 'unexpected_product_url'})
                continue
            accepted.append({'item_id': key, 'category': category, 'item': item,
                             'url': product_url,
                             'image_url': image.get('src', ''), 'text': text,
                             'price_text': price.get_text(' ', strip=True)})
    return accepted, rejected, result


def promotion_fields(product):
    """Recognized source terms only; unknown offer shapes fail publication review."""
    fields = dict.fromkeys(['volume_deals_description', 'volume_deals_price', 'digital_deals_description', 'digital_deals_price'], '')
    unknown = []
    for promo in product.get('promoData') or []:
        if promo.get('type') in FINANCE:
            continue
        text = promo.get('description') or promo.get('text') or promo.get('message') or ''
        if not isinstance(text, str):
            text = ''
        text = BeautifulSoup(text, 'html.parser').get_text(' ', strip=True)
        terms = promo.get('terms') or ''
        if terms and isinstance(terms, str):
            if terms.startswith(('http://', 'https://')):
                unknown.append({'reason': 'offer_terms_require_review', 'terms': terms})
            elif terms not in text:
                text += ' ' + BeautifulSoup(terms, 'html.parser').get_text(' ', strip=True)
        if re.search(r'walmart cash|cashback|cash back|manufacturer offer', text, re.I):
            continue  # Reward, not an immediate reduction in the checkout price.
        if re.search(r'clip|activate|digital coupon|add.*offer|save.*offer', text, re.I):
            kind = 'digital'
        elif re.search(r'\b\d+\s+for\s+\$|buy\s+\d|mix\s+or\s+match|must buy|when you buy', text, re.I):
            kind = 'volume'
        else:
            unknown.append(promo)
            continue
        fields[kind + '_deals_description'] += (' | ' if fields[kind + '_deals_description'] else '') + text
        # Only a final amount explicitly written in the offer, never a savings amount.
        match = re.search(r'(?:\b\d+\s+for\s+|\bat\s+)(\$\d+(?:\.\d{1,2})?)|^(\$\d+(?:\.\d{1,2})?)\s+each\b', text, re.I)
        if match:
            amount = money((match.group(1) or match.group(2))[1:])
            if fields[kind + '_deals_price'] and fields[kind + '_deals_price'] != amount:
                unknown.append({'reason': 'multiple_distinct_deal_prices', 'text': text})
            else:
                fields[kind + '_deals_price'] = amount
    if product.get('promoDiscount') or (product.get('priceInfo') or {}).get('volumePriceTiers'):
        unknown.append({'reason': 'structured_discount_requires_adapter_review'})
    return fields, unknown


def product_record(candidate, soup, store, private_labels, logo):
    product = next_data(soup).get('data', {}).get('product')
    if not product or str(product.get('usItemId')) != candidate['item_id']:
        raise ValueError('Product identity mismatch or missing response')
    location = product.get('location') or {}
    if location.get('intent') != 'PICKUP' or str((location.get('pickupLocation') or {}).get('storeId')) != str(store['id']):
        raise ValueError('Location mismatch: publication prohibited')
    if not pickup(product, store):
        return None, 'no_local_pickup', product
    if (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart.com', 'Walmart']:
        return None, 'marketplace', product
    if product.get('availabilityStatus') not in ['IN_STOCK', 'AVAILABLE']:
        return None, 'unavailable', product
    info = product.get('priceInfo') or {}
    title = product.get('name') or candidate['item'].get('name', '')
    if APPROX.search(title) or (info.get('priceDisplayCodes') or {}).get('finalCostByWeight'):
        return None, 'approximate_weight', product
    current = (info.get('currentPrice') or {}).get('price')
    displayed = re.search(r'(?:Price Now|Price) \$(\d+(?:\.\d{1,2})?)', candidate['price_text'])
    if current is None or not displayed or money(current) != money(displayed.group(1)):
        return None, 'price_changed', product
    promos, unknown = promotion_fields(product)
    if unknown:
        return None, 'promotion_review_required', product
    was = re.search(r'Was \$(\d+(?:\.\d{1,2})?)', candidate['price_text'])
    weight = WEIGHT.search(title)
    weight_text = weight.group() if weight else ''
    specs = next_data(soup).get('data', {}).get('idml', {}).get('specifications') or []
    for spec in specs:
        if spec.get('name', '').lower() in ['net weight', 'net content', 'net content weight', 'weight'] and isinstance(spec.get('value'), str):
            if APPROX.search(spec['value']):
                return None, 'approximate_weight', product
            if not weight_text and WEIGHT.search(spec['value']):
                weight_text = spec['value']
    ppm = PPM.search(candidate['price_text'])
    brand = product.get('brand') or ''
    row = dict.fromkeys(FIELDS, '')
    row.update(zipcode=store['zip'], store_name=store['name'], store_location=store['address'], store_logo=logo,
               store_brand=brand if brand in private_labels else 'no', category=candidate['category'],
               sub_category=(candidate['item'].get('category') or {}).get('categoryPath', '').split('/')[-1],
               product_title=title, weight=weight_text,
               regular_price=money(was.group(1) if was else current), sale_price=money(current) if was else '',
               image_url=candidate['image_url'], url=candidate['url'], upc=str(product.get('upc') or ''),
               ppm=ppm.group() if ppm else '', crawl_date=datetime.now(timezone.utc).isoformat())
    row.update(promos)
    return row, '', product


def category_id(url):
    path = urlsplit(url).path.rstrip('/').split('/')[-1]
    return path if re.fullmatch(r'\d+(?:_\d+)*', path) else ''


def discover(soup, root_url, exclusions, current_url=None):
    root_id = category_id(root_url)
    current_id = category_id(current_url or root_url)
    main = soup.select_one('main') or soup
    found = {}
    for a in main.select('a[href]'):
        url = urljoin('https://www.walmart.com', a['href'])
        parts = urlsplit(url)
        if parts.netloc != 'www.walmart.com' or not parts.path.startswith(('/cp/', '/browse/')):
            continue
        child_id = category_id(url)
        parent_reference = (parse_qs(parts.query).get('povid') or [''])[0]
        parent_link = any(parent_reference.startswith(parent + '_') for parent in [root_id, current_id])
        direct_landing_link = parts.path.startswith('/cp/') and urlsplit(current_url or root_url).path.startswith('/cp/')
        if not child_id or not (re.search(r'(?:^|_)' + re.escape(root_id) + r'(?:_|$)', child_id) or parent_link or direct_landing_link):
            continue
        name = a.get_text(' ', strip=True)
        if any((re.search(pattern, name, re.I) or re.search(pattern, parts.path, re.I)) for pattern in exclusions):
            continue
        # Tracking query strings do not define a new category.
        found[parts.scheme + '://' + parts.netloc + parts.path] = name
    return found
