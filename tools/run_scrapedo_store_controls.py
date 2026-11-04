"""Run the bounded Scrape.do Store 100 controls requested by provider support."""
import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


ITEMS = ['47428850', '10450114', '10450114']
STORE_ID = '100'
POSTAL_CODE = '72712'
REQUEST_LIMIT = 3
RETRY_LIMIT = 1
RUNTIME_LIMIT_SECONDS = 300
CREDIT_LIMIT = 30


def token():
    return subprocess.run(
        ['security', 'find-generic-password', '-s', 'walmart-scrapedo', '-a', 'ruddigarcia', '-w'],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def field(data, *path):
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def parse(body):
    soup = BeautifulSoup(body, 'html.parser')
    script = soup.select_one('#__NEXT_DATA__')
    if not script or not script.string:
        raise ValueError('Walmart __NEXT_DATA__ missing')
    data = json.loads(script.string)['props']['pageProps']['initialData']['data']
    product = data.get('product') or {}
    location = field(data, 'contentLayout', 'pageMetadata', 'location') or {}
    pickup = [value for value in product.get('fulfillmentOptions') or [] if value.get('type') == 'PICKUP']
    price = field(product, 'priceInfo', 'currentPrice') or {}
    return {
        'product_id': product.get('usItemId'),
        'store_id': location.get('storeId'),
        'pickup_store': location.get('pickupStore'),
        'postal_code': location.get('postalCode'),
        'city': location.get('city'),
        'state': location.get('stateOrProvinceCode'),
        'intent': location.get('intent'),
        'pickup_options': [
            {key: value.get(key) for key in ['type', 'locationText', 'availabilityStatus']}
            for value in pickup
        ],
        'price': price.get('price'),
        'currency': price.get('currencyUnit'),
    }


def accepted(result, item):
    return all([
        str(result.get('product_id')) == item,
        str(result.get('store_id')) == STORE_ID,
        str(result.get('pickup_store')) == STORE_ID,
        str(result.get('postal_code')) == POSTAL_CODE,
        result.get('intent') == 'PICKUP',
        bool(result.get('pickup_options')),
        result.get('price') is not None,
    ])


def fetch(api_token, item, timeout):
    target = f'https://www.walmart.com/ip/{item}'
    query = urllib.parse.urlencode({
        'token': api_token,
        'url': target,
        'zipcode': POSTAL_CODE,
        'storeid': STORE_ID,
    })
    request = urllib.request.Request(
        'https://api.scrape.do/plugin/walmart/store?' + query,
        headers={'User-Agent': 'walmart-scraper-bounded-control/1.0'},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_output', type=Path)
    parser.add_argument('public_result', type=Path)
    args = parser.parse_args()
    args.private_output.mkdir(parents=True, exist_ok=True)
    args.public_result.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    api_token = token()
    results = []
    requests = 0
    retries = 0
    queue = list(ITEMS)
    while queue and requests < REQUEST_LIMIT and time.monotonic() - started < RUNTIME_LIMIT_SECONDS:
        item = queue.pop(0)
        request_started = time.monotonic()
        status, body, headers = fetch(api_token, item, 90)
        requests += 1
        raw_path = args.private_output / f'request-{requests:02d}-{item}.html'
        raw_path.write_bytes(body)
        parsed = {}
        error = None
        if status == 200:
            try:
                parsed = parse(body)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as value:
                error = f'{type(value).__name__}: {value}'
        result = {
            'request_number': requests,
            'item_id_requested': item,
            'http_status': status,
            'seconds': round(time.monotonic() - request_started, 3),
            'body_bytes': len(body),
            'body_sha256': hashlib.sha256(body).hexdigest(),
            'fields': parsed,
            'accepted': status == 200 and accepted(parsed, item),
            'parse_error': error,
            'provider_usage_headers': {
                key: value for key, value in headers.items()
                if any(word in key.lower() for word in ['credit', 'cost', 'usage', 'request'])
            },
        }
        results.append(result)
        if status == 502 and retries < RETRY_LIMIT and requests < REQUEST_LIMIT:
            queue.insert(0, item)
            retries += 1

    credits_used = sum(
        int(result['provider_usage_headers'].get('scrape.do-request-cost', 0))
        for result in results
    )
    report = {
        'time_amsterdam': datetime.now(ZoneInfo('Europe/Amsterdam')).isoformat(),
        'provider_configuration': {
            'endpoint': 'https://api.scrape.do/plugin/walmart/store',
            'parameters': {'url': 'https://www.walmart.com/ip/{item_id}', 'zipcode': POSTAL_CODE, 'storeid': STORE_ID},
            'credential': 'macOS Keychain; not stored in evidence',
        },
        'limits': {
            'total_requests_including_retries': REQUEST_LIMIT,
            'retries': RETRY_LIMIT,
            'runtime_seconds': RUNTIME_LIMIT_SECONDS,
            'credits': CREDIT_LIMIT,
            'paid_cost_usd': 0,
        },
        'actual': {
            'requests_including_retries': requests,
            'retries': retries,
            'runtime_seconds': round(time.monotonic() - started, 3),
            'credits_used': credits_used,
            'remaining_credits_after_test': next((
                int(result['provider_usage_headers']['scrape.do-remaining-credits'])
                for result in reversed(results)
                if result['provider_usage_headers'].get('scrape.do-remaining-credits')
            ), None),
            'credit_limit_exceeded': credits_used > CREDIT_LIMIT,
            'paid_cost_usd': None,
            'paid_cost_note': 'No monetary charge was reported by the response; account credits are recorded separately.',
        },
        'required_context': {
            'store_id': STORE_ID,
            'postal_code': POSTAL_CODE,
            'fulfillment': 'PICKUP',
            'product_identity': True,
            'local_price': True,
        },
        'results': results,
        'all_responses_accepted': bool(results) and all(result['accepted'] for result in results),
        'large_collection_started': False,
        'raw_responses': 'Private ignored data directory only; public evidence contains hashes and selected fields.',
    }
    args.public_result.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({
        'requests': requests,
        'accepted': sum(result['accepted'] for result in results),
        'all_responses_accepted': report['all_responses_accepted'],
        'runtime_seconds': report['actual']['runtime_seconds'],
    }))


if __name__ == '__main__':
    main()
