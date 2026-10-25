"""Offline classification of observed links; uncertain links stay out of the test plan."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urljoin, urlsplit, parse_qs

from bs4 import BeautifulSoup
from extract import category_id
from storage import page_url


def classify(url, root_url, ancestors):
    parent = category_id(root_url)
    tokens = category_id(url).split('_')
    if category_id(url) == parent or (tokens[-1] == parent and len(tokens) > 1):
        return 'root_or_root_alias'
    if parent in tokens:
        return 'supported_descendant_id'
    if category_id(url) in ancestors:
        return 'broader_ancestor_not_descendant'
    return 'unresolved_independent_landing'


def review():
    source = Path('data/corrected-plan-20261025/step6-category-review')
    roots = json.loads((source / 'report.json').read_text())['categories']
    configured = {r['Category (Auto)']: page_url(r['URL']) for r in csv.DictReader(Path('config/categories.csv').open())}
    decisions, plan = [], []
    for index, entry in enumerate(roots, 1):
        snapshot = source / f'root-{index}.html'
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == entry['native_snapshot_sha256']
        page = BeautifulSoup(snapshot.read_bytes(), 'html.parser')
        anchors = defaultdict(list)
        for a in (page.select_one('main') or page).select('a[href]'):
            url = urljoin('https://www.walmart.com', a['href']); parts = urlsplit(url)
            canonical = parts.scheme + '://' + parts.netloc + parts.path
            anchors[canonical].append(a)
        root_url = configured[entry['category']]
        root_id = category_id(root_url)
        ancestors = set()
        for url in entry['discovered_child_urls']:
            ids = category_id(url).split('_')
            if root_id in ids:
                ancestors.update(ids[:ids.index(root_id)])
        supported = []
        for url in entry['discovered_child_urls']:
            assert anchors[url], 'Discovered URL missing from original native source'
            names = list(dict.fromkeys(a.get_text(' ', strip=True) for a in anchors[url]))
            status = classify(url, root_url, ancestors)
            row = dict(category=entry['category'], url=url, names=names[:5], classification=status,
                       source_snapshot_sha256=entry['native_snapshot_sha256'],
                       source_has_parent_tracking_reference=any((parse_qs(urlsplit(a['href']).query).get('povid') or [''])[0].startswith(root_id + '_') for a in anchors[url]))
            decisions.append(row)
            if status == 'supported_descendant_id':
                supported.append(row)
        if supported:
            chosen = min(supported, key=lambda x: (len(category_id(x['url']).split('_')), len(urlsplit(x['url']).path), x['url']))
            plan.append(dict(category=entry['category'], url=chosen['url'], required_root=root_url,
                             reason='Observed native link with explicit required-root ID ancestry',
                             source_snapshot_sha256=entry['native_snapshot_sha256']))
        page.decompose()
    assert len(decisions) == 683 and len({d['url'] for d in decisions}) == 680
    assert len(plan) <= 7
    out = Path('evidence/corrected-plan-20261025/step6-link-scope')
    out.mkdir(exist_ok=True)
    summary = dict(mode='Offline audit of seven prior live root DOM snapshots; no new requests',
                   occurrences_reviewed=len(decisions), unique_urls_reviewed=len({d['url'] for d in decisions}),
                   classification_counts=dict(Counter(d['classification'] for d in decisions)),
                   selected_test_pages=len(plan), full_coverage_complete=False,
                   scope_limit='ID ancestry supports a test choice, not exhaustive category correctness. Tracking references alone do not prove ancestry. Unresolved links retained for review, never silently removed from full-coverage obligations.')
    for name, value in [('summary.json', summary), ('decisions.json', decisions), ('bounded-plan.json', plan)]:
        (out / name).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(summary))
    print(json.dumps(plan))


if __name__ == '__main__':
    assert classify('https://www.walmart.com/browse/pets/dogs/5440_1', 'https://www.walmart.com/cp/pets/5440', set()) == 'supported_descendant_id'
    assert classify('https://www.walmart.com/cp/baby/5427', 'https://www.walmart.com/cp/feeding/133283', {'5427'}) == 'broader_ancestor_not_descendant'
    assert classify('https://www.walmart.com/cp/other/999?povid=5440_link', 'https://www.walmart.com/cp/pets/5440', set()) == 'unresolved_independent_landing'
    review()
