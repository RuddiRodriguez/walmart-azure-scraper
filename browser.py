"""Local Chrome session. Challenges and location changes stop collection."""
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from seleniumbase import sb_cdp

from extract import next_data, pickup


def open_browser(headless=False):
    options = {'locale': 'en', 'guest': True, 'headless': headless}
    profile = os.environ.get('WALMART_BROWSER_PROFILE')
    if profile:
        options.update(guest=False, user_data_dir=str(Path(profile).resolve()))
    proxy = os.environ.get('WALMART_PROXY_URL')
    if proxy:
        options['proxy'] = proxy
    return sb_cdp.Chrome(**options)


def check_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(' ', strip=True).lower() if soup.title else ''
    if not title:
        raise ValueError('Empty page title; page may still be loading')
    if any(t in title for t in ['robot or human', 'access denied', 'captcha']):
        raise ValueError('Challenge, access denial, or empty page; no automated CAPTCHA solving')
    return soup


def navigate(sb, url, settings, log, require_banner=True):
    for attempt in range(settings['retries']):
        started = time.monotonic()
        try:
            sb.goto(url)
            sb.sleep(settings['delay_seconds'])
            html = sb.get_page_source()
            for _ in range(12):
                pending = BeautifulSoup(html, 'html.parser')
                ready = bool(pending.title and pending.title.get_text(strip=True) and pending.select_one('#__NEXT_DATA__')
                             and (not require_banner or pending.select_one('[data-automation-id="fulfillment-banner"]')))
                pending.clear(decompose=True)
                pending.decompose()
                if ready:
                    break
                sb.sleep(1)
                html = sb.get_page_source()
            soup = check_html(html)
            next_data(soup)
            if require_banner and not soup.select_one('[data-automation-id="fulfillment-banner"]'):
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
    initial = navigate(sb, 'https://www.walmart.com/', settings, log)
    initial.clear(decompose=True)
    initial.decompose()
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
    store_label = 'label[for^="' + str(store['id']) + '-"]'
    store_radio = 'input[id^="' + str(store['id']) + '-"]'
    sb.click(store_label if sb.is_element_visible(store_label) else store_radio)
    sb.click('button:contains("Save")')
    sb.sleep(3)
    if not sb.is_element_visible('#intent-id1'):
        sb.click('[data-automation-id="fulfillment-banner"]')
    sb.click('#intent-id1')
    sb.sleep(3)
    soup = check_html(sb.get_page_source())
    verify_banner(soup, store)
    observed = {}
    for field in ['name', 'address']:
        node = soup.find(string=lambda text: text and text.strip() == store[field])
        if node is None:
            raise ValueError('Store ' + field + ' not present in retailer response')
        observed[field] = node.strip()
    store.update(observed)
    (output / 'selected-store.json').write_text(json.dumps({'id': str(store['id']), **observed, 'banner': soup.select_one('[data-automation-id="fulfillment-banner"]').get_text(' ', strip=True), 'source': 'visible retailer DOM strings verified against configured location'}, indent=2) + '\n')
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


def store_snapshot(sb, store, previous=None):
    """Observe store state; retain cookie values in memory, never in logs."""
    cookies = {(c.name, c.domain, c.path): c.value for c in sb.get_all_cookies()
               if c.name in ['locDataV3', 'locGuestData', 'assortmentStoreId']}
    changed = [] if previous is None else sorted({key[0] for key in cookies.keys() | previous.keys()
                                                 if cookies.get(key) != previous.get(key)})
    soup = BeautifulSoup(sb.get_page_source(), 'html.parser')
    banner = soup.select_one('[data-automation-id="fulfillment-banner"]')
    text = banner.get_text(' ', strip=True) if banner else ''
    soup.clear(decompose=True)
    soup.decompose()
    return {'banner': text, 'banner_matches': 'Pickup' in text and store['name'] in text,
            'location_cookie_names': sorted({key[0] for key in cookies}),
            'changed_location_cookie_names': changed}, cookies


def fetch_product(sb, url, settings, log=None, capture=None):
    # Abort the browser request too; cancelling Python's wait alone leaves fetch running.
    timeout_ms = max(1, int(settings['max_page_seconds'] * 1000))
    body = 'return {status:r.status, url:r.url, redirected:r.redirected, headers, html:await r.text()};'
    if capture:
        # Fetch exposes decoded body bytes, not compressed/TLS wire bytes.
        body = '''const reader = r.body.getReader(); const chunks = []; let length = 0;
        while (true) {
            const chunk = await reader.read(); if (chunk.done) break;
            length += chunk.value.length;
            if (length > 10485760) { await reader.cancel(); throw new Error("Diagnostic response exceeds 10 MiB"); }
            chunks.push(chunk.value);
        }
        const bytes = new Uint8Array(length); let offset = 0;
        for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
        let binary = "";
        for (let i=0; i<bytes.length; i+=16384) binary += String.fromCharCode(...bytes.subarray(i,i+16384));
        return {status:r.status, url:r.url, redirected:r.redirected, headers,
                html:new TextDecoder().decode(bytes), body_base64:btoa(binary)};'''
    expression = '(async () => { const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), ' + str(timeout_ms) + '); try { const r = await fetch(' + json.dumps(url) + ', {signal: controller.signal, cache: "no-store"}); const headers = Object.fromEntries(["date", "age", "cache-control", "cache-status", "x-cache", "vary", "content-type"].map(k => [k, r.headers.get(k)]).filter(v => v[1] !== null)); ' + body + ' } finally { clearTimeout(timer); } })()'
    for attempt in range(settings['retries']):
        started = time.monotonic()
        if capture:
            capture('request', url=url, attempt=attempt + 1, started_utc=datetime.now(timezone.utc).isoformat(),
                    settings={'method': 'GET', 'cache': 'no-store', 'credentials': 'same-origin (browser default)',
                              'redirect': 'follow (browser default)', 'timeout_seconds': settings['max_page_seconds'],
                              'configured_attempts': settings['retries'], 'request_headers': 'browser-managed; not captured'})
        try:
            result = sb.loop.run_until_complete(asyncio.wait_for(
                sb.page.evaluate(expression, await_promise=True), timeout=settings['max_page_seconds']))
            if capture:
                try:
                    capture('response', result=result, elapsed_seconds=round(time.monotonic() - started, 3),
                            received_utc=datetime.now(timezone.utc).isoformat())
                except Exception as error:
                    raise RuntimeError('Evidence capture failed; run stopped') from error
            if log:
                response_url = urlsplit(result.get('url', url))._replace(query='', fragment='').geturl()
                log('product_response', url=url, response_url=response_url, status=result['status'],
                    redirected=result.get('redirected', False), headers=result.get('headers', {}))
            if result['status'] in [401, 403, 412, 429]:
                raise ValueError(f"Access blocked: HTTP {result['status']}; run stopped")
            if result['status'] != 200:
                raise RuntimeError(f"Product HTTP {result['status']}")
            return check_html(result['html'])
        except Exception as error:
            if capture:
                capture('error', error_type=type(error).__name__, error=str(error))
            if log:
                log('product_retry', url=url, attempt=attempt + 1, error=str(error))
            if 'Evidence capture failed' in str(error) or 'Access blocked' in str(error) or 'Challenge' in str(error) or attempt + 1 == settings['retries']:
                raise
            time.sleep(settings['delay_seconds'] * (attempt + 2))


def canary_check(sb, store, settings):
    if not store.get('canary_urls'):
        raise ValueError('Configure at least one observed canary product per store')
    for url in store['canary_urls']:
        soup = fetch_product(sb, url, settings)
        try:
            product = next_data(soup).get('data', {}).get('product') or {}
        finally:
            soup.clear(decompose=True)
            soup.decompose()
        expected_id = re.search(r'/([0-9]+)(?:\?|$)', url)
        if expected_id and str(product.get('usItemId')) != expected_id.group(1):
            raise ValueError('Canary product identity mismatch')
        if (product.get('sellerName') or product.get('sellerDisplayName')) not in ['Walmart', 'Walmart.com']:
            raise ValueError('Canary seller changed')
        location = product.get('location') or {}
        if (location.get('intent') != 'PICKUP'
                or str((location.get('pickupLocation') or {}).get('storeId')) != str(store['id'])
                or str(location.get('postalCode') or '') != store['zip']
                or not pickup(product, store)):
            raise ValueError('Canary missing or incorrect store context')
