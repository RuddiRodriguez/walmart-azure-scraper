"""Short live page-readiness observation; never collects or publishes products."""
import hashlib
import json
import signal
from pathlib import Path
from datetime import datetime, timezone

from browser import open_browser, select_store, navigate, store_snapshot
from extract import next_data

output = Path(__file__).parent
settings = json.loads(Path('config/stores.json').read_text())
settings.update(retries=1, max_page_seconds=25)
store = settings['stores'][0]
result = {'mode': 'short live banner observation; not a crawl or fix', 'observations': []}
sb = None
cookies = None

def log(event, **values):
    with (output / 'events.jsonl').open('a') as f:
        f.write(json.dumps({'time': datetime.now(timezone.utc).isoformat(), 'event': event, **values}) + '\n')

def stop(*_):
    raise TimeoutError('180-second diagnostic limit')

signal.signal(signal.SIGALRM, stop)
signal.alarm(180)
try:
    sb = open_browser()
    select_store(sb, store, settings, log, output)
    for index, category in enumerate(['diapering/486190', 'feeding/133283', 'diapering/486190', 'feeding/133283']):
        page = navigate(sb, 'https://www.walmart.com/cp/' + category, settings, log)
        page.decompose()
        for delay in [0, 2, 3]:
            if delay:
                sb.sleep(delay)
            state, cookies = store_snapshot(sb, store, cookies)
            html = sb.get_page_source()
            name = str(index) + '-' + str(delay) + '.html'
            (output / name).write_text(html)
            result['observations'].append({'category': category, 'delay': delay,
                'source_sha256': hashlib.sha256(html.encode()).hexdigest(), **state})
            (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
except Exception as error:
    result['error'] = str(error)
finally:
    signal.alarm(0)
    if sb:
        sb.driver.stop()
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
