"""Local Chrome session. Challenges and location changes stop collection."""
import asyncio
import json
import re
import time

from bs4 import BeautifulSoup
from seleniumbase import sb_cdp

from extract import next_data, pickup


def open_browser():
    return sb_cdp.Chrome(locale='en', guest=True, headless=False)


def check_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(' ', strip=True).lower() if soup.title else ''
    if not title:
        raise ValueError('Empty page title; page may still be loading')
    if any(t in title for t in ['robot or human', 'access denied', 'captcha']):
        raise ValueError('Challenge, access denial, or empty page; no automated CAPTCHA solving')
    return soup


def navigate(sb, url, settings, log):
    for attempt in range(settings['retries']):
        started = time.monotonic()
        try:
            sb.goto(url)
            sb.sleep(settings['delay_seconds'])
            html = sb.get_page_source()
            for _ in range(12):
                pending = BeautifulSoup(html, 'html.parser')
                if pending.title and pending.title.get_text(strip=True) and pending.select_one('#__NEXT_DATA__') and pending.select_one('[data-automation-id="fulfillment-banner"]'):
                    break
                sb.sleep(1)
                html = sb.get_page_source()
            soup = check_html(html)
            next_data(soup)
            if not soup.select_one('[data-automation-id="fulfillment-banner"]'):
                raise ValueError('Store banner not loaded; retry incomplete page')
            elapsed = time.monotonic() - started
            if elapsed > settings['max_page_seconds']:
                raise TimeoutError(f'Abnormal page latency: {elapsed:.1f}s')
            log('page_loaded', url=url, seconds=round(elapsed, 2))
            return soup
        except Exception as error:
            log('retry', url=url, attempt=attempt + 1, error=str(error))
            if 'Challenge' in str(error) or attempt + 1 == settings['retries']:
                raise
            sb.sleep(settings['delay_seconds'] * (attempt + 2))


def select_store(sb, store, settings, log, output):
    sb.goto('https://www.walmart.com/')
    sb.sleep(4)
    sb.click('[data-automation-id="fulfillment-banner"]')
    sb.sleep(2)
    soup = BeautifulSoup(sb.get_page_source(), 'html.parser')
    # The current address changes with IP/location. Use the visible address button.
    addresses = [b.get_text(' ', strip=True) for b in soup.select('button:not([data-automation-id="fulfillment-banner"])')
                 if re_address(b.get_text(' ', strip=True))]
    if not addresses:
        (output / 'store-selector.html').write_text(str(soup))
        raise ValueError('Store selector changed; address control not found')
    street = re.search(r'\b\d+\s+[^,]+', addresses[0]).group()
    sb.click('button:contains(' + json.dumps(street) + ')')
    sb.sleep(2)
    sb.type('#zip-code-or-city-state', store['zip'])
    sb.press_keys('#zip-code-or-city-state', '\n')
    sb.sleep(3)
    sb.click('input[id^="' + str(store['id']) + '-"]')
    sb.click('button:contains("Save")')
    sb.sleep(3)
    if not sb.is_element_visible('#intent-id1'):
        sb.click('[data-automation-id="fulfillment-banner"]')
    sb.click('#intent-id1')
    sb.sleep(3)
    soup = check_html(sb.get_page_source())
    verify_banner(soup, store)
    sb.save_screenshot(str(output / 'selected-store.png'))
    logo = soup.select_one('a[aria-label="Walmart Homepage"] img')
    log('store_selected', store=store['id'], name=store['name'], zip=store['zip'], fulfillment='PICKUP')
    return logo.get('src', '') if logo else ''


def re_address(text):
    import re
    return bool(re.search(r'\b\d+\s+.{2,60}\b(?:ROAD|RD|STREET|ST|BLVD|BOULEVARD|AVE|AVENUE|DR|DRIVE|WAY)\b', text, re.I))


def verify_banner(soup, store):
    banner = soup.select_one('[data-automation-id="fulfillment-banner"]')
    text = banner.get_text(' ', strip=True) if banner else ''
    if not banner:
        raise ValueError('Store banner missing; location cannot be verified')
    if 'Pickup' not in text or store['name'] not in text:
        raise ValueError('Location mismatch in store banner')


def fetch_product(sb, url, settings):
    expression = 'fetch(' + json.dumps(url) + ').then(async r => ({status:r.status, html:await r.text()}))'
    for attempt in range(settings['retries']):
        try:
            result = sb.loop.run_until_complete(asyncio.wait_for(
                sb.page.evaluate(expression, await_promise=True), timeout=settings['max_page_seconds']))
            if result['status'] in [401, 403, 429]:
                raise ValueError(f"Access blocked: HTTP {result['status']}; run stopped")
            if result['status'] != 200:
                raise RuntimeError(f"Product HTTP {result['status']}")
            return check_html(result['html'])
        except Exception as error:
            if 'Access blocked' in str(error) or 'Challenge' in str(error) or attempt + 1 == settings['retries']:
                raise
            time.sleep(settings['delay_seconds'] * (attempt + 2))


def canary_check(sb, store, settings):
    if not store.get('canary_urls'):
        raise ValueError('Configure at least one observed canary product per store')
    for url in store['canary_urls']:
        soup = fetch_product(sb, url, settings)
        product = next_data(soup).get('data', {}).get('product') or {}
        expected_id = re.search(r'/([0-9]+)(?:\?|$)', url)
        if expected_id and str(product.get('usItemId')) != expected_id.group(1):
            raise ValueError('Canary product identity mismatch')
        if (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart', 'Walmart.com']:
            raise ValueError('Canary seller changed')
        location = product.get('location') or {}
        if (location.get('intent') != 'PICKUP'
                or str((location.get('pickupLocation') or {}).get('storeId')) != str(store['id'])
                or not pickup(product, store)):
            raise ValueError('Canary missing or incorrect store context')
