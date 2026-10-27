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
ROOT_IDS = {
    'Food': '976759', 'Household Essentials': '1115193', 'Personal Care': '1005862',
    'Beauty': '1085666', 'Diapering': '5427_486190', 'Feeding': '133283',
    'Health & Wellness': '976760', 'Pets': '5440',
    'Balloons': '2637_1042319_1212898_3956207', 'Art Supplies': '5899871',
    'Office Supplies': '1229749',
}


def next_data(soup):
    node = soup.select_one('#__NEXT_DATA__')
    if not node:
        raise ValueError('Missing retailer data: response may be incomplete or blocked')
    return json.loads(node.string)['props']['pageProps'].get('initialData', {})


def scope(category, item):
    details = item.get('category') or {}
    expected = ROOT_IDS.get(category, '').split('_')
    actual = str(details.get('categoryPathId') or '').split(':')
    path = str(details.get('categoryPath') or '')
    inside = any(actual[index:index + len(expected)] == expected
                 for index in range(len(actual) - len(expected) + 1)) if expected else False
    return inside and 'farm animals' not in path.lower()


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
            unavailable = item.get('availabilityStatus') in ['OUT_OF_STOCK', 'UNAVAILABLE']
            if not key.isdigit() or not link or not image:
                rejected.append({'item_id': key, 'reason': 'missing_listing_fields'})
                continue
            product_url = urljoin('https://www.walmart.com', link['href'])
            if urlsplit(product_url).netloc != 'www.walmart.com' or not urlsplit(product_url).path.startswith('/ip/'):
                rejected.append({'item_id': key, 'reason': 'unexpected_product_url'})
                continue
            accepted.append({'item_id': key, 'category': category, 'item': item,
                             'url': product_url,
                             'image_url': image.get('src', ''), 'text': text,
                             'price_text': price.get_text(' ', strip=True) if price else '',
                             'local_pickup_at_listing': pickup(item, store)})
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
        match = re.search(r'(?:\b\d+\s+for\s+|\bat\s+|:\s*(?=\$\d+(?:\.\d{1,2})?\s+each))(\$\d+(?:\.\d{1,2})?)|^(\$\d+(?:\.\d{1,2})?)\s+each\b', text, re.I)
        if match:
            amount = money((match.group(1) or match.group(2))[1:])
            if fields[kind + '_deals_price'] and fields[kind + '_deals_price'] != amount:
                unknown.append({'reason': 'multiple_distinct_deal_prices', 'text': text})
            else:
                fields[kind + '_deals_price'] = amount
    if product.get('promoDiscount') or (product.get('priceInfo') or {}).get('volumePriceTiers'):
        unknown.append({'reason': 'structured_discount_requires_adapter_review'})
    return fields, unknown


def product_record(candidate, soup, store, private_labels, logo, retain_missing=False, known_store_assortment=False):
    product = next_data(soup).get('data', {}).get('product')
    if not product or str(product.get('usItemId')) != candidate['item_id']:
        raise ValueError('Product identity mismatch or missing response')
    location = product.get('location') or {}
    if location.get('intent') != 'PICKUP' or str((location.get('pickupLocation') or {}).get('storeId')) != str(store['id']):
        raise ValueError('Location mismatch: publication prohibited')
    if str(location.get('postalCode') or '') != store['zip']:
        raise ValueError('Location ZIP mismatch: publication prohibited')
    has_pickup_offer = pickup(product, store)
    local_out_of_stock = any(option.get('type') == 'PICKUP'
                             and option.get('locationText') == store['name']
                             and option.get('availabilityStatus') == 'OUT_OF_STOCK'
                             for option in product.get('fulfillmentOptions') or [])
    from retention import product_state
    state = product_state(candidate, product, store, known_store_assortment) if retain_missing else None
    if not retain_missing and not has_pickup_offer and not local_out_of_stock:
        return None, 'no_local_pickup', product
    seller = product.get('sellerName') or product.get('sellerDisplayName')
    if retain_missing and not seller:
        seller = candidate['item'].get('sellerName')  # Retain listing-proven retailer items when unavailable PDP omits seller.
    if seller not in ['Walmart.com', 'Walmart']:
        return None, 'marketplace', product
    unavailable = local_out_of_stock or product.get('availabilityStatus') in ['OUT_OF_STOCK', 'UNAVAILABLE']
    if not retain_missing and not local_out_of_stock and product.get('availabilityStatus') not in ['IN_STOCK', 'AVAILABLE', 'OUT_OF_STOCK', 'UNAVAILABLE']:
        return None, 'unknown_availability', product
    info = product.get('priceInfo') or {}
    title = product.get('name') or candidate['item'].get('name', '')
    if APPROX.search(title) or (info.get('priceDisplayCodes') or {}).get('finalCostByWeight'):
        return None, 'approximate_weight', product
    # No local offer means any displayed shipping price must not enter the local export.
    local_price_unknown = state != 'available' if retain_missing else local_out_of_stock and not has_pickup_offer
    current = None if local_price_unknown else (info.get('currentPrice') or {}).get('price')
    displayed = None if local_price_unknown else re.search(r'(?:Price Now|Price) \$(\d+(?:\.\d{1,2})?)', candidate['price_text'])
    missing_unavailable_price = unavailable and current is None and not displayed
    price_unverified = not missing_unavailable_price and (current is None or not displayed or money(current) != money(displayed.group(1)))
    if price_unverified:
        if not retain_missing:
            return None, 'price_changed', product
        local_price_unknown = True
        current = displayed = None
    promos, unknown = promotion_fields({} if local_price_unknown else product)
    if unknown:
        return None, 'promotion_review_required', product
    was = None if local_price_unknown else re.search(r'Was \$(\d+(?:\.\d{1,2})?)', candidate['price_text'])
    weight = WEIGHT.search(title)
    weight_text = weight.group() if weight else ''
    specs = (next_data(soup).get('data', {}).get('idml') or {}).get('specifications') or []
    for spec in specs:
        if spec.get('name', '').lower() in ['net weight', 'net content', 'net content weight', 'weight'] and isinstance(spec.get('value'), str):
            if APPROX.search(spec['value']):
                return None, 'approximate_weight', product
            if not weight_text and WEIGHT.search(spec['value']):
                weight_text = spec['value']
    ppm = None if local_price_unknown else PPM.search(candidate['price_text'])
    brand = product.get('brand') or ''
    row = dict.fromkeys(FIELDS, '')
    row.update(zipcode=str(location.get('postalCode') or ''), store_name=store['name'], store_location=store['address'], store_logo=logo,
               store_brand=brand if brand in private_labels else 'no', category=candidate['category'],
               sub_category=(candidate['item'].get('category') or {}).get('categoryPath', '').split('/')[-1],
               product_title=title, weight=weight_text,
               regular_price=money(was.group(1) if was else current), sale_price=money(current) if was else '',
               image_url=candidate['image_url'], url=candidate['url'], upc=str(product.get('upc') or ''),
               ppm=ppm.group() if ppm else '', crawl_date=datetime.now(timezone.utc).isoformat())
    row.update(promos)
    if retain_missing:
        reason = {'assortment_unverified':'retained_assortment_unverified',
                  'confirmed_unavailable':'retained_unavailable',
                  'confirmed_no_pickup_offer':'retained_no_pickup_offer',
                  'pickup_evidence_missing':'retained_pickup_evidence_missing',
                  'availability_evidence_missing':'retained_availability_evidence_missing'}.get(state, '')
        if not reason and price_unverified:
            reason = 'retained_price_evidence_missing'
        return row, reason, product
    return row, 'retained_unavailable' if unavailable else '', product


def listing_record(candidate, cached, store, private_labels, logo):
    """Refresh changing fields from a verified listing while reusing stable cached details."""
    if not cached or not candidate.get('listing_store_verified'):
        return None, 'product_detail_required'
    item = candidate['item']
    unavailable = item.get('availabilityStatus') in ['OUT_OF_STOCK', 'UNAVAILABLE']
    has_pickup = candidate.get('local_pickup_at_listing', False) or pickup(item, store)
    if not unavailable and not has_pickup:
        return None, 'product_detail_required'
    info = item.get('priceInfo') or {}
    current = None if unavailable or not has_pickup else (info.get('currentPrice') or {}).get('price')
    displayed = None if current is None else re.search(r'(?:Price Now|Price) \$(\d+(?:\.\d{1,2})?)', candidate['price_text'])
    if current is not None and (not displayed or money(current) != money(displayed.group(1))):
        return None, 'price_changed'
    promos, unknown = promotion_fields({} if current is None else item)
    if unknown:
        return None, 'promotion_review_required'
    was = None if current is None else re.search(r'Was \$(\d+(?:\.\d{1,2})?)', candidate['price_text'])
    ppm = None if current is None else PPM.search(candidate['price_text'])
    title = item.get('name') or cached['product_title']
    weight = WEIGHT.search(title)
    brand = item.get('brand') or ''
    row = dict.fromkeys(FIELDS, '')
    row.update(zipcode=store['zip'], store_name=store['name'], store_location=store['address'], store_logo=logo or cached['store_logo'],
               store_brand=brand if brand in private_labels else cached['store_brand'], category=candidate['category'],
               sub_category=(item.get('category') or {}).get('categoryPath', '').split('/')[-1],
               product_title=title, weight=weight.group() if weight else cached['weight'],
               regular_price=money(was.group(1) if was else current), sale_price=money(current) if was else '',
               image_url=candidate['image_url'], url=candidate['url'], upc=cached['upc'],
               ppm=ppm.group() if ppm else '', crawl_date=datetime.now(timezone.utc).isoformat())
    row.update(promos)
    return row, 'retained_unavailable' if unavailable else ('retained_no_pickup_offer' if not has_pickup else '')


def category_id(url):
    path = urlsplit(url).path.rstrip('/').split('/')[-1]
    return path if re.fullmatch(r'\d+(?:_\d+)*', path) else ''


def descendant_id(parent, child):
    """True only when child continues parent's retailer category path."""
    parent_parts = parent.split('_')
    child_parts = child.split('_')
    return any(child_parts[index:index + len(parent_parts)] == parent_parts
               and index + len(parent_parts) < len(child_parts)
               for index in range(len(child_parts) - len(parent_parts) + 1))


def discover(soup, root_url, exclusions, current_url=None, decisions=None):
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
        if not child_id:
            continue
        name = a.get_text(' ', strip=True)
        canonical = parts.scheme + '://' + parts.netloc + parts.path
        reason = ''
        if not descendant_id(root_id, child_id):
            reason = 'outside_required_category'
        elif not descendant_id(current_id, child_id):
            reason = 'not_descendant_of_current_category'
        if any((re.search(pattern, name, re.I) or re.search(pattern, parts.path, re.I)) for pattern in exclusions):
            reason = 'brief_exclusion'
        if decisions is not None:
            decisions.append({'url': canonical, 'name': name, 'action': 'skipped' if reason else 'queued', 'reason': reason or 'category_link'})
        if reason:
            continue
        # Tracking query strings do not define a new category.
        found[parts.scheme + '://' + parts.netloc + parts.path] = name
    return found
