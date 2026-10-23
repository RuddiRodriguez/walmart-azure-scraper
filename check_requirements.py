"""Offline requirement checks. Synthetic variants are never presented as live evidence."""
import copy
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from browser import check_html, verify_banner
from extract import listing_candidates, product_record, promotion_fields, discover
from validate import validate


def run():
    settings = json.loads(Path('config/stores.json').read_text())
    store = settings['stores'][0]
    source = json.loads(Path('evidence/source-records.json').read_text())[0]
    row = json.loads(Path('evidence/products-500.json').read_text())[0]
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append(name)

    def valid(rows, **kwargs):
        return validate(rows, [row['category']], store, {**settings, 'minimum_records': 1}, 0, 0, 0, **kwargs)['passed']

    check('Captured historical record passes schema checks', valid([row]))
    for name, change in [
        ('null field', {'weight': None}), ('wrong price format', {'regular_price': '1,00'}),
        ('wrong store ZIP', {'zipcode': '99999'}), ('wrong address', {'store_location': 'Other store'}),
        ('generated GUPC', {'gupc': '123'}), ('calculated unit price', {'unit_price': '1.00'}),
        ('approximate weight', {'weight': 'approximately 2 lb'}), ('unknown category', {'category': 'Other'}),
        ('missing date timezone', {'crawl_date': '2026-10-23T00:00:00'}),
        ('invalid date', {'crawl_date': 'today'}), ('missing title', {'product_title': ''}),
        ('non-retailer URL', {'url': 'https://example.com/ip/123'})]:
        check('Rejects ' + name, not valid([{**row, **change}]))
    missing = dict(row); missing.pop('upc')
    check('Missing schema key returns failure without crashing', not valid([missing]))
    check('Reordered schema rejected', not valid([dict(reversed(list(row.items())))]))
    check('Non-object record returns failure', not valid([None]))
    check('Duplicate URLs rejected', not valid([row, row]))
    check('Same product ID with different query rejected', not valid([row, {**row, 'url': row['url'] + '&review=1'}]))
    check('Material category decline rejected', not valid([row], previous={'category_counts': {row['category']: 100}}))
    check('Pending pages prevent publication', not validate([row], [row['category']], store, {**settings, 'minimum_records': 1}, 1, 0, 0)['passed'])
    check('Pending products prevent publication', not validate([row], [row['category']], store, {**settings, 'minimum_records': 1}, 0, 1, 0)['passed'])
    check('Unresolved product review prevents publication', not validate([row], [row['category']], store, {**settings, 'minimum_records': 1}, 0, 0, 1)['passed'])

    def parse(product):
        soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
        soup.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {'product': product}}}}})
        return product_record(source['candidate'], soup, store, settings['private_labels'], '')

    for name, mutate, expected in [
        ('Shipping-only product', lambda p: p.update(fulfillmentSummary=[]), 'no_local_pickup'),
        ('Marketplace product', lambda p: p.update(sellerName='Other seller'), 'marketplace'),
        ('Unknown availability', lambda p: p.update(availabilityStatus='MYSTERY'), 'unknown_availability'),
        ('Changed price', lambda p: p['priceInfo']['currentPrice'].update(price=99999), 'price_changed'),
        ('Approximate weight', lambda p: p.update(name='Approximately 2 lb'), 'approximate_weight'),
        ('Unknown promotion', lambda p: p.update(promoData=[{'text': 'Mystery special'}]), 'promotion_review_required')]:
        product = copy.deepcopy(source['product']); mutate(product)
        record, reason, _ = parse(product)
        check(name + ' excluded with explicit reason', record is None and reason == expected)
    product = copy.deepcopy(source['product']); product['location']['postalCode'] = '99999'
    try:
        parse(product)
    except ValueError as error:
        check('Wrong response ZIP fails', 'ZIP mismatch' in str(error))
    else:
        raise AssertionError('Wrong ZIP accepted')

    for text, kind, amount in [
        ('2 for $5. Limit 4.', 'volume', '5.00'), ('Buy 1, Get 1 Free', 'volume', ''),
        ('Save $5 when you buy 5', 'volume', ''), ('Mix or Match 5 for $10', 'volume', '10.00'),
        ('Must buy 4: $1.99 each', 'volume', '1.99'), ('Clip Coupon: Save $2', 'digital', ''),
        ('$3.99 each with Digital Coupon', 'digital', '3.99'), ('20% off with clipped coupon', 'digital', ''),
        ('Save $5 when you buy 5 with Digital Coupon', 'digital', '')]:
        fields, unknown = promotion_fields({'promoData': [{'text': text}]})
        check('Promotion wording and explicit price: ' + text, not unknown and fields[kind + '_deals_description'] == text and fields[kind + '_deals_price'] == amount)
    fields, unknown = promotion_fields({'promoData': [{'text': 'Earn $3 Walmart Cash'}]})
    check('Walmart Cash not turned into a discount', not unknown and not any(fields.values()))
    _, unknown = promotion_fields({'promoData': [{'text': '2 for $5', 'terms': 'https://example.com/terms'}]})
    check('Unread linked offer terms require review', bool(unknown))

    item = copy.deepcopy(source['candidate']['item'])
    def listing(value):
        soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
        soup.script.string = json.dumps({'props': {'pageProps': {'initialData': {'searchResult': {'itemStacks': [{'items': [value]}]}}}}})
        return listing_candidates(soup, source['candidate']['category'], store)
    item['isSponsoredFlag'] = True
    check('Sponsored structured product excluded', listing(item)[1][0]['reason'] == 'sponsored')
    item['isSponsoredFlag'] = False; item['sponsoredProduct'] = None; item['sellerName'] = 'Other'
    check('Marketplace listing excluded', listing(item)[1][0]['reason'] == 'marketplace')
    item['sellerName'] = 'Walmart.com'; item['fulfillmentSummary'] = []
    check('Shipping-only listing excluded', listing(item)[1][0]['reason'] == 'no_local_pickup')

    for title in ['Robot or human?', 'Access Denied', 'CAPTCHA']:
        try:
            check_html('<title>' + title + '</title>')
        except ValueError:
            checks.append('Challenge rejected: ' + title)
        else:
            raise AssertionError('Challenge accepted')
    try:
        verify_banner(BeautifulSoup('<button data-automation-id="fulfillment-banner">Shipping Other store</button>', 'html.parser'), store)
    except ValueError:
        checks.append('Wrong banner rejected')
    else:
        raise AssertionError('Wrong banner accepted')
    decisions = []
    soup = BeautifulSoup('<main><a href="/browse/batteries/1115193_1076905?povid=976759_Crossmerch">Batteries</a><a href="/browse/food/bread/976759_976779">Bread</a><a href="/cp/recipes/123?povid=976759_Categories">Recipes</a></main>', 'html.parser')
    links = discover(soup, 'https://www.walmart.com/cp/food/976759', ['recipes'], decisions=decisions)
    check('Unrelated browse ancestry and recipes skipped with reasons', len(links) == 1 and len([d for d in decisions if d['action'] == 'skipped']) == 2)
    composite = BeautifulSoup('<main><a href="/browse/baby/5427_486190_123">Child</a></main>', 'html.parser')
    check('Composite root ID retains its child category', bool(discover(composite, 'https://www.walmart.com/browse/diapering/5427_486190', [])))
    report = {'mode': 'offline checks of captured evidence and explicitly synthetic mutations; no live acceptance claim',
              'time_utc': datetime.now(timezone.utc).isoformat(), 'passed': True, 'count': len(checks), 'checks': checks}
    Path('evidence/requirements-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
