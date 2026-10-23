"""Offline regression checks using a captured response plus explicitly synthetic variants."""
import copy
import json
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from extract import product_record
from storage import connect, add_pages, save_page, save_product, records
from validate import validate
from scrape import run as scrape_run


def run():
    settings = json.loads(Path('config/stores.json').read_text())
    store = settings['stores'][0]
    source = json.loads(Path('evidence/source-records.json').read_text())[0]
    results = []

    def parse(item):
        soup = BeautifulSoup('<script id="__NEXT_DATA__"></script>', 'html.parser')
        soup.script.string = json.dumps({'props': {'pageProps': {'initialData': {'data': {'product': item['product']}}}}})
        return product_record(item['candidate'], soup, store, settings['private_labels'], '')

    unavailable = copy.deepcopy(source)
    unavailable['product']['availabilityStatus'] = 'OUT_OF_STOCK'
    row, reason, _ = parse(unavailable)
    assert row and reason == 'retained_unavailable'
    results.append('Synthetic unavailable item with explicit local pickup and matching displayed price retained')
    unavailable['product']['priceInfo']['currentPrice'] = {}
    unavailable['candidate']['price_text'] = ''
    row, reason, _ = parse(unavailable)
    assert row and row['regular_price'] == row['sale_price'] == ''
    report = validate([row], [row['category']], store, {**settings, 'minimum_records': 1}, 0, 0, 0, unavailable_urls={row['url']})
    assert report['passed']
    assert not validate([row], [row['category']], store, {**settings, 'minimum_records': 1}, 0, 0, 0)['passed']
    results.append('Missing price retained only with unavailable evidence; normal missing-price record rejected')
    local_unavailable = copy.deepcopy(source)
    local_unavailable['product']['fulfillmentSummary'] = []
    local_unavailable['product']['availabilityStatus'] = 'IN_STOCK'  # Shipping remains available.
    local_unavailable['product']['fulfillmentOptions'] = [
        {'type': 'PICKUP', 'locationText': store['name'], 'availabilityStatus': 'OUT_OF_STOCK'}]
    retained, reason, _ = parse(local_unavailable)
    assert retained and reason == 'retained_unavailable'
    assert all(retained[field] == '' for field in ['regular_price', 'sale_price', 'ppm', 'volume_deals_price', 'digital_deals_price'])
    results.append('Explicit store-specific out-of-stock status retained without copying shipping prices or PPM')
    local_unavailable['product']['fulfillmentOptions'][0]['locationText'] = 'Different store'
    assert parse(local_unavailable)[1] == 'no_local_pickup'
    local_unavailable['product']['fulfillmentOptions'][0].update(locationText=store['name'], availabilityStatus='NOT_AVAILABLE')
    assert parse(local_unavailable)[1] == 'no_local_pickup'
    results.append('Different-store and not-available pickup options do not prove local out-of-stock inventory')
    wrong_store = copy.deepcopy(source)
    wrong_store['product']['location']['pickupLocation']['storeId'] = '999999'
    try:
        parse(wrong_store)
    except ValueError as error:
        assert 'Location mismatch' in str(error)
    else:
        raise AssertionError('Wrong store accepted')
    results.append('Synthetic wrong-store detail rejected')
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'checkpoint.sqlite'
        db = connect(path)
        candidate = source['candidate']
        with db:
            add_pages(db, candidate['category'], ['page1'])
        save_page(db, candidate['category'], 'page1', ['page2'], [candidate], [], 1)
        save_product(db, candidate, row, reason)
        db.close()
        db = connect(path)
        assert db.execute("SELECT url FROM pages WHERE status='pending'").fetchall() == [('page2',)]
        assert db.execute("SELECT count(*) FROM candidates WHERE status='pending'").fetchone()[0] == 0
        assert len(records(db)) == 1
        db.close()
    results.append('Offline checkpoint close/reopen keeps completed product and pending next page')
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder) / '100'
        base.mkdir()
        prior = b'{"run_id":"prior-good-output"}\n'
        (base / 'latest.json').write_bytes(prior)
        args = Namespace(config='config/stores.json', categories='config/categories.csv',
                         store='100', output=folder, resume=False, sample=0)
        with patch('scrape.open_browser', side_effect=ValueError('Offline simulated access block')):
            try:
                scrape_run(args)
            except ValueError as error:
                assert str(error) == 'Offline simulated access block'
            else:
                raise AssertionError('Simulated access failure did not stop run')
        assert (base / 'latest.json').read_bytes() == prior
        failure = next((base / 'runs').glob('*/failure.json'))
        assert json.loads(failure.read_text())['published'] is False
        assert json.loads((failure.parent / 'products.partial.json').read_text()) == []
    results.append('Offline simulated access failure exports partial evidence and leaves prior publication byte-identical')
    Path('evidence/review-regression.json').write_text(json.dumps({
        'mode': 'offline checks; availability variants are synthetic, not observed live offers',
        'passed': True, 'checks': results,
    }, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    run()
