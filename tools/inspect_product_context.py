"""Compare same-session fetch and visible navigation for a failed product's fulfillment context."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from browser import open_browser, select_store, fetch_product, navigate, canary_check
from extract import next_data
from storage import atomic_json


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('failure', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    url = json.loads(args.failure.read_text())['current_work']['url']
    settings = json.loads(Path('config/stores.json').read_text()); store = settings['stores'][0]
    args.output.mkdir(parents=True, exist_ok=True)
    def log(event, **values):
        entry = {'time':datetime.now(timezone.utc).isoformat(), 'event':event, **values}
        with (args.output/'events.jsonl').open('a') as stream:stream.write(json.dumps(entry)+'\n')
        print(json.dumps(entry), flush=True)
    sb = None
    try:
        sb = open_browser(); select_store(sb,store,settings,log,args.output); canary_check(sb,store,settings)
        for mode in ['fetch','navigate']:
            soup = fetch_product(sb,url,settings,log) if mode == 'fetch' else navigate(sb,url,settings,log)
            product = next_data(soup).get('data',{}).get('product') or {}
            banner = soup.select_one('[data-automation-id="fulfillment-banner"]')
            result = {'mode':mode, 'url':url, 'time_utc':datetime.now(timezone.utc).isoformat(), 'banner':banner.get_text(' ',strip=True) if banner else '',
                      'product':{key:product.get(key) for key in ['usItemId','name','availabilityStatus','sellerName','sellerDisplayName','location','fulfillmentSummary','fulfillmentOptions','priceInfo']}}
            atomic_json(args.output/(mode+'.json'),result)
            log('context_probe', mode=mode, location=product.get('location'), availability=product.get('availabilityStatus'))
            if mode == 'navigate':sb.save_screenshot(str(args.output/'product.png'))
        canary_check(sb,store,settings)
    except BaseException as error:
        atomic_json(args.output/'failure.json', {'error':str(error),'type':type(error).__name__})
        if sb:
            try:sb.save_screenshot(str(args.output/'failure.png'))
            except Exception:pass
        raise
    finally:
        if sb:sb.quit()
