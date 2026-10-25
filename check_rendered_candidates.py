"""Offline checks for rendered cards matched to captured listing data."""
import copy
import json
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup
from capture_store_drift import listing_from_rendered


def check():
    source = json.loads(Path('evidence/source-records.json').read_text())[0]
    candidate = source['candidate']
    item = candidate['item']
    store = json.loads(Path('config/stores.json').read_text())['stores'][0]
    outsider = {**item, 'id': 'not-in-captured-listing', 'usItemId': '999999999'}

    def document(items, store_id='100', page=1, cards=False):
        soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
        search = {'paginationV2': {'pageProperties': {'stores': store_id, 'facet': 'fulfillment_method:Pickup', 'page': page}},
                  'itemStacks': [{'items': items}]}
        soup.script.string = json.dumps({'props': {'pageProps': {'initialData': {'searchResult': search}}}})
        if cards:
            for product in items:
                card = soup.new_tag('div', attrs={'data-item-id': product['id']})
                link = soup.new_tag('a', href=candidate['url']); card.append(link)
                image = soup.new_tag('img', attrs={'data-testid': 'productTileImage', 'src': candidate['image_url']}); card.append(image)
                price = soup.new_tag('span', attrs={'data-testid': 'unified-global-product-price-a11y-text'})
                price.string = candidate['price_text']; card.append(price); soup.append(card)
        return soup

    checks = []
    with tempfile.TemporaryDirectory() as folder:
        native = Path(folder) / 'native.html'
        native.write_text(str(document([item, outsider], cards=True)))
        fetched = document([item])
        accepted, _, _ = listing_from_rendered(native, fetched, candidate['category'], store)
        assert [c['item_id'] for c in accepted] == [candidate['item_id']]
        checks.append('Rendered-only outsider excluded; accepted IDs belong to captured primary listing')
        assert accepted[0]['price_text'] == candidate['price_text']
        checks.append('Visible price retained for independent product-response comparison')
        sponsored = copy.deepcopy(item); sponsored['isSponsoredFlag'] = True
        assert not listing_from_rendered(native, document([sponsored]), candidate['category'], store)[0]
        checks.append('Captured sponsored flag rejects otherwise visible native card')
        for fetched in [document([item], store_id='3081'), document([item], page=2)]:
            try:
                listing_from_rendered(native, fetched, candidate['category'], store)
            except ValueError:
                pass
            else:
                raise AssertionError('Contradictory captured context accepted')
        checks.append('Wrong store and mismatched native/captured page rejected')
    out = Path('evidence/corrected-plan-20261025/step3-review/rendered-candidate-checks.json')
    out.write_text(json.dumps({'mode': 'Offline synthetic cards and captured historical item fixture; zero live requests',
                               'passed': True, 'checks': checks}, indent=2) + '\n')
    print(json.dumps({'passed': True, 'checks': len(checks), 'live_requests': 0}))


if __name__ == '__main__':
    check()
