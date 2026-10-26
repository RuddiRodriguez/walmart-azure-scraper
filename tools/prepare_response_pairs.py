"""Prepare allowlist-redacted copies of two existing response pairs; never scrape or send."""
import hashlib
import json
from pathlib import Path
import subprocess
from bs4 import BeautifulSoup
from extract import next_data
from storage import atomic_json

PAIRS = ['controlled-500-20261025', 'controlled-500-continuation-20261025']
PUBLIC_PRODUCT = ['usItemId', 'name', 'upc', 'sellerName', 'sellerDisplayName', 'availabilityStatus', 'priceInfo']
PUBLIC_LOCATION = ['postalCode', 'stateOrProvinceCode', 'city', 'storeIds', 'intent']
PUBLIC_FULFILLMENT = ['type', 'intent', 'selected', 'availabilityStatus', 'inventoryStatus', 'availableQuantity', 'maxOrderQuantity', 'orderLimit']
MARKER = '[redacted]'


def select(value, keys):
    return {k: value[k] for k in keys if k in value}


def redact(original, public_price):
    soup = BeautifulSoup(original, 'html.parser')
    product = next_data(soup)['data']['product']
    if product['priceInfo'] != public_price:
        raise ValueError('Price subtree differs from already public reviewed metadata')
    kept = select(product, PUBLIC_PRODUCT)
    location = product.get('location') or {}
    kept['location'] = select(location, PUBLIC_LOCATION)
    kept['location']['pickupLocation'] = select(location.get('pickupLocation') or {}, ['storeId', 'accessType'])
    kept['fulfillmentOptions'] = [select(v, PUBLIC_FULFILLMENT) for v in product.get('fulfillmentOptions') or []]
    data = dict(props=dict(pageProps=dict(initialData=dict(data=dict(product=kept, redacted=MARKER)))))
    script = soup.find('script', id='__NEXT_DATA__')
    for node in soup.find_all(True):
        node.attrs = {'id': '__NEXT_DATA__'} if node is script else {}
    for node in list(soup.find_all(string=True)):
        node.replace_with(MARKER)
    script.string = json.dumps(data).replace('</', '<\\/')
    output = str(soup).encode()
    # Independent structural privacy gate: only retained JSON, marker text and bare tags survive.
    checked = BeautifulSoup(output, 'html.parser')
    assert next_data(checked)['data']['product'] == kept
    for node in checked.find_all(True):
        assert node.attrs == ({'id': '__NEXT_DATA__'} if node.name == 'script' and node.get('id') == '__NEXT_DATA__' else {})
    for text in checked.find_all(string=True):
        assert not str(text).replace(MARKER, '') or text.parent.get('id') == '__NEXT_DATA__'
    return output, kept


def build():
    output = Path('evidence/response-pairs-reviewed-20261026')
    output.mkdir(exist_ok=True)
    result = dict(scope='Privacy-reviewed redacted response documents from complete private Fetch-decoded originals; no new live requests',
                  demonstration=dict(store='100', address='406 S Walton Blvd, Bentonville, AR 72712', fulfillment='PICKUP'),
                  redaction='All HTML attributes and text redacted except one allowlisted product JSON subtree; other original JSON replaced. HTML reserialized, not byte-identical original. No reconstructed product/store/price values.',
                  pairs=[], client_sent=False, transport_remedy_proven=False)
    for folder in PAIRS:
        run = Path('data') / folder
        report = json.loads((run / 'report.json').read_text())
        metadata = json.loads((Path('evidence') / folder / 'raw-pair-metadata.json').read_text())
        for name, digest in report['source_hashes'].items():
            assert hashlib.sha256(subprocess.check_output(['git', 'show', report['source_commit'] + ':' + name])).hexdigest() == digest
        pair = dict(run=folder, source_commit=report['source_commit'], source_hashes=report['source_hashes'],
                    retry_behavior='One diagnostic same-session re-fetch of identical URL/settings after rejected context; failed run stayed invalid. No new session; no cure claimed.', responses=[])
        for member in metadata['pair']:
            sequence = member['sequence']
            capture_path = run / 'captures' / f'collection-{sequence:03}.json'
            capture = json.loads(capture_path.read_text())
            original_path = capture_path.parent / capture['body_file']
            original = original_path.read_bytes()
            digest = hashlib.sha256(original).hexdigest()
            assert digest == capture['body_sha256'] == member['body_sha256']
            assert len(original) == capture['body_bytes'] == member['body_bytes']
            redacted, product = redact(original, member['price_context'])
            filename = folder + '-' + member['role'] + '.redacted.html'
            (output / filename).write_bytes(redacted)
            assert str(product['usItemId']) == member['product_id']
            assert str(product['location']['pickupLocation']['storeId']) == member['store_id']
            assert product['location']['intent'] == member['intent']
            assert product['location']['postalCode'] == member['zip']
            row = dict(role=member['role'], sequence=sequence, original_private_path=str(original_path),
                       original_body_sha256=digest, original_bytes=len(original), redacted_path=str(output / filename),
                       redacted_sha256=hashlib.sha256(redacted).hexdigest(), retained_product=product,
                       request=member['request'], response=member['response'], source_values_unchanged=True,
                       original_scope='Complete decoded bytes returned by browser Fetch; not wire/TLS capture')
            # Export only request/response metadata already published in the older evidence.
            assert row['request'] == capture['request']
            assert row['response'] == capture['response']
            pair['responses'].append(row)
        wrong, corrected = pair['responses']
        assert wrong['sequence'] + 1 == corrected['sequence']
        assert wrong['request']['url'] == corrected['request']['url']
        assert wrong['request']['settings'] == corrected['request']['settings']
        assert corrected['retained_product']['location']['pickupLocation']['storeId'] == '100'
        assert corrected['retained_product']['location']['intent'] == 'PICKUP'
        result['pairs'].append(pair)
    atomic_json(output / 'reviewed-pairs.json', result)
    atomic_json(output / 'SHA256SUMS.json', {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.json'})
    print(json.dumps(dict(pairs=len(result['pairs']), responses=sum(len(p['responses']) for p in result['pairs']), original_hashes_verified=True, source_commits_verified=True, retained_fields_verified=True, structural_privacy_checks_passed=True, sent=False)))


if __name__ == '__main__':
    build()
