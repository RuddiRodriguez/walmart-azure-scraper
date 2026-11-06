"""Run an approved, bounded Scrape.do Walmart listing control.

This file is executable, but it must not be run without separate client approval.
"""
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


STORE_ID = '100'
POSTAL_CODE = '72712'
LISTING_URL = ('https://www.walmart.com/browse/personal-care/toothpaste/'
               '1005862_1007221_1023020?page=1')
EXPECTED_CATEGORY_ID = '1005862_1007221_1023020'
CONTROL_SEQUENCE = [LISTING_URL, LISTING_URL]
REQUEST_LIMIT = 3
RETRY_LIMIT = 1
RUNTIME_LIMIT_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 90
DEADLINE_BUFFER_SECONDS = 5
CREDIT_LIMIT = 60
CREDIT_RESERVATION_PER_REQUEST = 20
RESPONSE_LIMIT_BYTES = 8 * 1024 * 1024
TOTAL_BODY_LIMIT_BYTES = 20 * 1024 * 1024
ALLOWED_PICKUP_STATES = {'IN_STOCK', 'AVAILABLE'}


class ResponseTooLarge(ValueError):
    pass


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def token():
    return subprocess.run(
        ['security', 'find-generic-password', '-s', 'walmart-scrapedo',
         '-a', 'ruddigarcia', '-w'],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def field(data, *path):
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def category_id(url):
    return url.split('/browse/', 1)[-1].split('?', 1)[0].rsplit('/', 1)[-1]


def pickup_option(item):
    options = item.get('fulfillmentOptions') or []
    for option in options:
        if (option.get('type') == 'PICKUP'
                and option.get('selected') is True
                and option.get('intent') is True
                and option.get('availabilityStatus') in ALLOWED_PICKUP_STATES):
            return option
    return None


def pickup_is_linked(item, option):
    if not option:
        return False
    types = item.get('availableFulfillmentOptions') or []
    if 'PICKUP' in types:
        return True
    return any(value.get('fulfillment') == 'PICKUP'
               for value in item.get('fulfillmentSummary') or [])


def parse_listing(body, requested_url):
    soup = BeautifulSoup(body, 'html.parser')
    script = soup.select_one('#__NEXT_DATA__')
    if not script or not script.string:
        raise ValueError('Walmart __NEXT_DATA__ missing')
    data = json.loads(script.string)['props']['pageProps']['initialData']['data']
    location = field(data, 'contentLayout', 'pageMetadata', 'location') or {}
    search = data.get('searchResult') or {}
    properties = field(search, 'paginationV2', 'pageProperties') or {}
    found_category = (field(search, 'catInfo', 'catId')
                      or properties.get('cat_id')
                      or properties.get('catId'))
    products = []
    for stack in search.get('itemStacks') or []:
        for item in stack.get('items') or []:
            if item.get('__typename') != 'Product':
                continue
            option = pickup_option(item)
            price = field(item, 'priceInfo', 'currentPrice') or {}
            product_id = str(item.get('usItemId') or '')
            price_value = price.get('price')
            linked = pickup_is_linked(item, option)
            if product_id.isdigit() and price_value is not None and linked:
                products.append({
                    'product_id': product_id,
                    'price': price_value,
                    'currency': price.get('currencyUnit'),
                    'pickup_availability': option.get('availabilityStatus'),
                    'pickup_selected': option.get('selected'),
                    'pickup_intent': option.get('intent'),
                    'source_paths': {
                        'product': 'searchResult.itemStacks[].items[]',
                        'price': 'product.priceInfo.currentPrice.price',
                        'pickup': 'product.fulfillmentOptions[type=PICKUP]',
                        'link': 'product.availableFulfillmentOptions or product.fulfillmentSummary',
                    },
                })
    return {
        'requested_category_id': category_id(requested_url),
        'returned_category_id': str(found_category or ''),
        'store_id': str(location.get('storeId') or ''),
        'pickup_store': str(location.get('pickupStore') or ''),
        'postal_code': str(location.get('postalCode') or ''),
        'intent': location.get('intent'),
        'products_with_bound_price_and_pickup': products,
    }


def accepted(result):
    return all([
        result.get('requested_category_id') == EXPECTED_CATEGORY_ID,
        result.get('returned_category_id') == EXPECTED_CATEGORY_ID,
        result.get('store_id') == STORE_ID,
        result.get('pickup_store') == STORE_ID,
        result.get('postal_code') == POSTAL_CODE,
        result.get('intent') == 'PICKUP',
        bool(result.get('products_with_bound_price_and_pickup')),
    ])


def read_bounded(response, byte_limit):
    body = response.read(byte_limit + 1)
    if len(body) > byte_limit:
        raise ResponseTooLarge(f'response exceeded {byte_limit} bytes')
    return body


def fetch(api_token, target, timeout, byte_limit):
    query = urllib.parse.urlencode({
        'token': api_token,
        'url': target,
        'zipcode': POSTAL_CODE,
        'storeid': STORE_ID,
    })
    request = urllib.request.Request(
        'https://api.scrape.do/plugin/walmart/store?' + query,
        headers={'User-Agent': 'walmart-scraper-bounded-listing-control/1.0'},
    )
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, read_bounded(response, byte_limit), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, read_bounded(error, byte_limit), dict(error.headers)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def initial_state(now):
    return {
        'version': 1,
        'started_unix': now,
        'deadline_unix': now + RUNTIME_LIMIT_SECONDS,
        'attempts_dispatched': 0,
        'retries_used': 0,
        'credits_accounted': 0,
        'body_bytes': 0,
        'next_control': 0,
        'in_flight': None,
        'results': [],
        'stop_reason': None,
        'completed': False,
    }


def usage_cost(headers):
    values = {key.lower(): value for key, value in headers.items()}
    raw = values.get('scrape.do-request-cost')
    if raw is None:
        raise ValueError('provider credit header missing; usage is uncertain')
    try:
        cost = int(raw)
    except (TypeError, ValueError) as error:
        raise ValueError('provider credit header is not an integer; usage is uncertain') from error
    if cost < 0:
        raise ValueError('provider credit header is negative; usage is uncertain')
    return cost


def public_report(state):
    results = [{key: value for key, value in result.items() if key != 'raw_path'}
               for result in state['results']]
    return {
        'time_amsterdam': datetime.now(ZoneInfo('Europe/Amsterdam')).isoformat(),
        'status': 'passed' if state['completed'] else 'stopped',
        'executed': bool(state['attempts_dispatched']),
        'completed_intended_sequence': state['completed'],
        'provider_configuration': {
            'endpoint': 'https://api.scrape.do/plugin/walmart/store',
            'listing_url': LISTING_URL,
            'zipcode': POSTAL_CODE,
            'storeid': STORE_ID,
            'credential': 'macOS Keychain; never written to evidence',
            'redirects': 'disabled',
            'fallbacks': 'disabled',
        },
        'limits': {
            'requests_including_retry': REQUEST_LIMIT,
            'retries': RETRY_LIMIT,
            'runtime_seconds': RUNTIME_LIMIT_SECONDS,
            'credits': CREDIT_LIMIT,
            'credit_reservation_per_request': CREDIT_RESERVATION_PER_REQUEST,
            'response_bytes': RESPONSE_LIMIT_BYTES,
            'total_body_bytes': TOTAL_BODY_LIMIT_BYTES,
            'paid_cost_usd': 0,
        },
        'actual': {
            'attempts_dispatched': state['attempts_dispatched'],
            'retries_used': state['retries_used'],
            'credits_accounted': state['credits_accounted'],
            'body_bytes': state['body_bytes'],
            'controls_completed': state['next_control'],
        },
        'stop_reason': state['stop_reason'],
        'uncertain_attempt': state['in_flight'],
        'results': results,
        'provider_charging_uncertainty': (
            'Reservations use the documented proposal limit, but the provider may report '
            'unexpected usage. Missing, invalid or excessive usage stops the run and remains '
            'uncertain; it is never counted as zero.'),
        'scope': 'Bounded listing control only; no coverage queue changes or publication.',
    }


def run(private_output, public_result, fetcher=fetch, clock=time.time, get_token=token):
    private_output.mkdir(parents=True, exist_ok=True)
    public_result.parent.mkdir(parents=True, exist_ok=True)
    state_path = private_output / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else initial_state(clock())
    if state['completed']:
        save_json(public_result, public_report(state))
        return state
    if state['in_flight']:
        state['stop_reason'] = 'persisted uncertain in-flight attempt requires manual reconciliation'
        save_json(state_path, state)
        save_json(public_result, public_report(state))
        return state
    if state['stop_reason']:
        save_json(public_result, public_report(state))
        return state
    api_token = None
    while state['next_control'] < len(CONTROL_SEQUENCE):
        remaining = state['deadline_unix'] - clock()
        if remaining <= DEADLINE_BUFFER_SECONDS:
            state['stop_reason'] = 'insufficient time before the persisted absolute deadline'
            break
        if state['attempts_dispatched'] >= REQUEST_LIMIT:
            state['stop_reason'] = 'request limit reached before intended sequence completed'
            break
        if state['credits_accounted'] + CREDIT_RESERVATION_PER_REQUEST > CREDIT_LIMIT:
            state['stop_reason'] = 'credit reservation would exceed cumulative limit'
            break
        body_limit = min(RESPONSE_LIMIT_BYTES, TOTAL_BODY_LIMIT_BYTES - state['body_bytes'])
        if body_limit <= 0:
            state['stop_reason'] = 'total response-byte limit reached'
            break
        if api_token is None:
            api_token = get_token()
        remaining = state['deadline_unix'] - clock()
        if remaining <= DEADLINE_BUFFER_SECONDS:
            state['stop_reason'] = 'insufficient time before the persisted absolute deadline'
            break
        attempt = state['attempts_dispatched'] + 1
        control = state['next_control'] + 1
        state['attempts_dispatched'] = attempt
        state['in_flight'] = {
            'attempt': attempt,
            'control': control,
            'reserved_credits': CREDIT_RESERVATION_PER_REQUEST,
            'started_unix': clock(),
        }
        save_json(state_path, state)
        timeout = min(REQUEST_TIMEOUT_SECONDS, max(1, int(remaining - DEADLINE_BUFFER_SECONDS)))
        started = clock()
        try:
            status, body, headers = fetcher(api_token, CONTROL_SEQUENCE[state['next_control']],
                                            timeout, body_limit)
        except Exception as error:
            state['stop_reason'] = f'uncertain request outcome: {type(error).__name__}: {error}'
            save_json(state_path, state)
            break
        raw_path = private_output / f'attempt-{attempt:02d}-control-{control:02d}.html'
        raw_path.write_bytes(body)
        state['body_bytes'] += len(body)
        try:
            cost = usage_cost(headers)
        except ValueError as error:
            state['in_flight']['http_status'] = status
            state['in_flight']['body_sha256'] = hashlib.sha256(body).hexdigest()
            state['stop_reason'] = str(error)
            save_json(state_path, state)
            break
        state['credits_accounted'] += cost
        state['in_flight'] = None
        result = {
            'attempt': attempt,
            'control': control,
            'http_status': status,
            'seconds': round(clock() - started, 3),
            'body_bytes': len(body),
            'body_sha256': hashlib.sha256(body).hexdigest(),
            'provider_credits': cost,
            'provider_usage_headers': {
                key: value for key, value in headers.items()
                if key.lower() in {
                    'scrape.do-request-cost',
                    'scrape.do-remaining-credits',
                    'scrape.do-request-id',
                }
            },
            'fields': {},
            'accepted': False,
            'parse_error': None,
            'raw_path': str(raw_path),
        }
        if cost > CREDIT_RESERVATION_PER_REQUEST or state['credits_accounted'] > CREDIT_LIMIT:
            state['stop_reason'] = 'provider usage exceeded the reserved or cumulative limit'
            state['results'].append(result)
            save_json(state_path, state)
            break
        if status == 502 and state['retries_used'] < RETRY_LIMIT:
            state['retries_used'] += 1
            state['results'].append(result)
            save_json(state_path, state)
            continue
        if status != 200:
            state['stop_reason'] = f'HTTP {status}; no fallback or redirect allowed'
            state['results'].append(result)
            save_json(state_path, state)
            break
        try:
            result['fields'] = parse_listing(body, CONTROL_SEQUENCE[state['next_control']])
            result['accepted'] = accepted(result['fields'])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            result['parse_error'] = f'{type(error).__name__}: {error}'
        state['results'].append(result)
        if not result['accepted']:
            state['stop_reason'] = 'listing context or price/PICKUP source linkage rejected'
            save_json(state_path, state)
            break
        state['next_control'] += 1
        save_json(state_path, state)
    state['completed'] = (state['next_control'] == len(CONTROL_SEQUENCE)
                          and state['stop_reason'] is None
                          and state['in_flight'] is None)
    save_json(state_path, state)
    save_json(public_result, public_report(state))
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_output', type=Path)
    parser.add_argument('public_result', type=Path)
    parser.add_argument('--approved', action='store_true')
    args = parser.parse_args()
    if not args.approved:
        raise SystemExit('Not executed: separate client approval and --approved are required.')
    state = run(args.private_output, args.public_result)
    print(json.dumps({
        'completed': state['completed'],
        'controls_completed': state['next_control'],
        'attempts': state['attempts_dispatched'],
        'stop_reason': state['stop_reason'],
    }))


if __name__ == '__main__':
    main()
