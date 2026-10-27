"""Short offline checks for category URL tracking aliases and pagination."""
import json
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from storage import connect, add_pages, page_url, product_url


def check():
    base = 'https://www.walmart.com/browse/beauty/1085666'
    aliases = [base, base + '#', base + '?povid=menu', base + '?athbdg=L1200#top']
    assert {page_url(url) for url in aliases} == {base}
    next_page = base + '?page=2&povid=menu&facet=brand%3AExample&empty=#top'
    canonical = page_url(next_page)
    assert parse_qs(urlsplit(canonical).query, keep_blank_values=True) == {'page': ['2'], 'facet': ['brand:Example'], 'empty': ['']}
    assert canonical != base and page_url(canonical) == canonical
    product = ('https://www.walmart.com/ip/Example/123?fulfillmentIntent=Pickup'
               '&filters=pickup&classType=VARIANT&athbdg=L1600&povid=tracking#top')
    assert product_url(product) == ('https://www.walmart.com/ip/Example/123'
                                    '?fulfillmentIntent=Pickup&classType=VARIANT')
    with tempfile.TemporaryDirectory() as folder:
        db = connect(Path(folder) / 'checkpoint.sqlite')
        with db:
            add_pages(db, 'Beauty', aliases + [next_page])
            add_pages(db, 'Personal Care', [base])
        rows = db.execute('SELECT category,url FROM pages ORDER BY category,url').fetchall()
        assert len(rows) == 3
        assert ('Beauty', canonical) in rows
        db.close()
    historical = json.loads(Path('evidence/full-attempt-v3-final/coverage.json').read_text())
    before = {(r['category'], r['url']) for r in historical}
    after = {(r['category'], page_url(r['url'])) for r in historical}
    result = {'mode': 'offline synthetic regressions and saved queue analysis; no fresh collection', 'passed': True,
              'checks': ['Tracking and fragment aliases collapse', 'Pagination, filters and blank parameters retained',
                         'Product URL keeps identity and functional context without tracking',
                         'Normalization is idempotent', 'Queue deduplicates within each category without merging categories'],
              'historical_queue_entries': len(before), 'normalized_entries': len(after), 'redundant_entries': len(before)-len(after)}
    Path('evidence/page-url-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    check()
