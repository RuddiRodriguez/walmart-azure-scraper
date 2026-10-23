"""Fresh, bounded investigation of genuine previously observed unavailable items."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from browser import open_browser, select_store, fetch_product, canary_check
from extract import next_data
from storage import atomic_json


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('evidence/unavailable-live-probe'))
    args = parser.parse_args()
    settings = json.loads(Path('config/stores.json').read_text()); store = settings['stores'][0]
    observations = json.loads(Path('evidence/observed-unavailable-offers.json').read_text())['cases']
    selected = {}
    for item in observations:
        if item['availabilityStatus'] in ['OUT_OF_STOCK', 'UNAVAILABLE'] and item['sellerName'] == 'Walmart.com':
            selected.setdefault(str(item['id']), item)
    output = args.output; output.mkdir(parents=True, exist_ok=True)
    def log(event, **values):
        entry = {'time': datetime.now(timezone.utc).isoformat(), 'event': event, **values}
        with (output / 'events.jsonl').open('a') as stream:stream.write(json.dumps(entry)+'\n')
        print(json.dumps(entry), flush=True)
    sb = None; results = []
    try:
        sb = open_browser(); select_store(sb, store, settings, log, output); canary_check(sb, store, settings)
        for key, prior in list(selected.items())[:6]:
            url = 'https://www.walmart.com/ip/' + key + '?fulfillmentIntent=Pickup'
            soup = fetch_product(sb, url, settings, log)
            product = next_data(soup).get('data', {}).get('product') or {}
            fields = ['usItemId','name','sellerName','sellerDisplayName','availabilityStatus','location','priceInfo','fulfillmentSummary','fulfillmentOptions','availabilityInNearbyStore']
            results.append({'url': url, 'checked_utc': datetime.now(timezone.utc).isoformat(), 'previous_listing_source': prior['source_file'],
                            'previous_availability': prior['availabilityStatus'], 'product': {k: product.get(k) for k in fields}})
            atomic_json(output/'products.json', results)
            log('unavailable_probe', id=key, availability=product.get('availabilityStatus'), fulfillment_options=product.get('fulfillmentOptions'))
            time.sleep(settings['delay_seconds'])
        atomic_json(output/'summary.json', {'mode':'fresh live investigation of previously unavailable listing items; not a complete catalog run', 'checked':len(results), 'unavailable_now':sum(r['product']['availabilityStatus'] in ['OUT_OF_STOCK','UNAVAILABLE'] for r in results)})
    except BaseException as error:
        if sb:
            try:
                local = Path('data') / output.name; local.mkdir(parents=True, exist_ok=True)
                (local/'failure.html').write_text(sb.get_page_source())
                sb.save_screenshot(str(output/'failure.png'))
            except Exception:
                pass
        atomic_json(output/'failure.json', {'error':str(error),'checked':len(results)})
        raise
    finally:
        if sb:sb.quit()
