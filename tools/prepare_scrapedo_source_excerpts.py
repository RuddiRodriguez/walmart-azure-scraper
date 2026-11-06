"""Create bounded, privacy-reviewed excerpts from saved Scrape.do responses."""
import argparse
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def field(data, *path):
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def selected(value, keys):
    return {key: value.get(key) for key in keys if value.get(key) is not None}


def excerpt(raw, filename):
    soup = BeautifulSoup(raw, 'html.parser')
    script = soup.select_one('#__NEXT_DATA__')
    if not script or not script.string:
        raise ValueError(f'Walmart __NEXT_DATA__ missing in {filename}')
    data = json.loads(script.string)['props']['pageProps']['initialData']['data']
    location = field(data, 'contentLayout', 'pageMetadata', 'location') or {}
    product = data.get('product') or {}
    price = field(product, 'priceInfo', 'currentPrice') or {}
    pickup = next((option for option in product.get('fulfillmentOptions') or []
                   if option.get('type') == 'PICKUP'), {})
    fulfillment_price = field(pickup, 'speedDetails', 'fulfillmentPrice')
    availability = pickup.get('availabilityStatus')
    currently_available = availability in {'IN_STOCK', 'AVAILABLE'}
    price_claim = ('displayed product price with currently available PICKUP context'
                   if currently_available else
                   'displayed product price only; not a currently available PICKUP offer')
    return {
        'source_file': filename,
        'source_paths': {
            'location': 'props.pageProps.initialData.data.contentLayout.pageMetadata.location',
            'product': 'props.pageProps.initialData.data.product',
            'price': 'product.priceInfo.currentPrice',
            'pickup': 'product.fulfillmentOptions[type=PICKUP]',
        },
        'location': selected(location, [
            'storeId', 'pickupStore', 'postalCode', 'city',
            'stateOrProvinceCode', 'intent',
        ]),
        'product': {
            'usItemId': product.get('usItemId'),
            'name': product.get('name'),
        },
        'displayed_price': selected(price, ['price', 'priceString', 'priceDisplay', 'currencyUnit']),
        'pickup': selected(pickup, [
            'type', 'selected', 'intent', 'locationText', 'availabilityStatus',
        ]),
        'review': {
            'pickup_currently_available': currently_available,
            'price_claim': price_claim,
            'price_binding': (
                'The displayed price and PICKUP option belong to the same product object under '
                'the Store 100 page context. The PICKUP option does not contain its own price.'),
            'fulfillment_specific_price': fulfillment_price,
            'limitation': (
                'This excerpt does not claim a fulfillment-specific price when the source field '
                'is empty.'),
        },
    }


def build(source, output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        'scope': 'Bounded fields selected from three saved product-control HTML responses.',
        'redaction': {
            'method': 'Allowlist extraction from Walmart __NEXT_DATA__; raw HTML is not copied.',
            'kept': [
                'product identity', 'Store 100 location fields', 'ZIP 72712',
                'PICKUP option and availability', 'displayed product price',
            ],
            'removed': [
                'all other HTML and scripts', 'cookies', 'request headers', 'provider token',
                'account data', 'unselected page content',
            ],
            'raw_location': 'Private ignored data directory; not published.',
        },
        'files': [],
    }
    for raw_path in sorted(source.glob('request-*.html')):
        raw = raw_path.read_bytes()
        value = excerpt(raw, raw_path.name)
        excerpt_path = output / raw_path.name.replace('.html', '-excerpt.json')
        excerpt_bytes = (json.dumps(value, indent=2) + '\n').encode()
        excerpt_path.write_bytes(excerpt_bytes)
        manifest['files'].append({
            'source_file': raw_path.name,
            'original_bytes': len(raw),
            'original_sha256': sha256(raw),
            'excerpt_file': excerpt_path.name,
            'excerpt_bytes': len(excerpt_bytes),
            'excerpt_sha256': sha256(excerpt_bytes),
        })
    if len(manifest['files']) != 3:
        raise ValueError(f'Expected three source responses, found {len(manifest["files"])}')
    (output / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'files': len(manifest['files']), 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build(args.source, args.output)
