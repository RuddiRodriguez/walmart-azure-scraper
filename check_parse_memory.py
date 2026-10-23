"""Offline parsing allocation comparison; not a browser or long-run memory benchmark."""
import gc
import json
import tracemalloc
from pathlib import Path
from bs4 import BeautifulSoup


def measure(release):
    gc.collect()
    gc.disable()
    tracemalloc.start()
    try:
        for _ in range(20):
            soup = BeautifulSoup('<html><body>' + '<div data-item-id="1"><span>Product</span></div>' * 200 + '</body></html>', 'html.parser')
            assert len(soup.select('[data-item-id]')) == 200
            if release:
                soup.clear(decompose=True)
                soup.decompose()
            del soup
        retained, peak = tracemalloc.get_traced_memory()
        return {'retained_bytes': retained, 'peak_bytes': peak}
    finally:
        tracemalloc.stop()
        gc.enable()
        gc.collect()


if __name__ == '__main__':
    before = measure(False)
    after = measure(True)
    result = {'mode': 'offline synthetic HTML; cyclic collection deliberately disabled to measure retained parse trees',
              'without_explicit_release': before, 'with_explicit_release': after,
              'passed': after['retained_bytes'] < before['retained_bytes'] / 2,
              'limit': 'Does not measure Chrome memory or establish the cause of previous system swap pressure.'}
    Path('evidence/parse-memory-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    assert result['passed']
