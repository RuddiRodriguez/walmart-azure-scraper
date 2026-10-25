"""Offline review of unresolved landing aliases and newly discovered category links."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit
from extract import category_id
from review_discovered_scope import classify
from storage import page_url


def review():
    base = Path('evidence/corrected-plan-20261025')
    original = json.loads((base / 'step6-link-scope/decisions.json').read_text())
    old_urls = {d['url'] for d in original}
    roots = {r['Category (Auto)']: page_url(r['URL']) for r in csv.DictReader(Path('config/categories.csv').open())}
    groups = [('step6-category-review', json.loads((base / 'step6-category-review/root-decisions.json').read_text())),
              ('step6-descendant-review', json.loads((base / 'step6-link-scope/descendant-decisions.json').read_text()))]
    observed = defaultdict(dict)
    for folder, entries in groups:
        for index, entry in enumerate(entries, 1):
            snapshot = Path('data/corrected-plan-20261025') / folder / f'root-{index}.html'
            assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == entry['native_snapshot_sha256']
            page = BeautifulSoup(snapshot.read_bytes(), 'html.parser')
            anchors = set()
            for a in (page.select_one('main') or page).select('a[href]'):
                p = urlsplit(urljoin('https://www.walmart.com', a['href']))
                anchors.add(p.scheme + '://' + p.netloc + p.path)
            for url in entry['discovered_child_urls']:
                assert url in anchors
                observed[entry['category']][url] = entry['native_snapshot_sha256']
            page.decompose()
    evidence = defaultdict(dict)
    for name, urls in observed.items():
        parent = category_id(roots[name])
        for url in urls:
            ids = category_id(url).split('_')
            if parent in ids[:-1]:
                evidence[name].setdefault(ids[-1], url)
    unresolved = [d for d in original if d['classification'] == 'unresolved_independent_landing']
    remaining = []
    for row in unresolved:
        proof = evidence[row['category']].get(category_id(row['url']))
        remaining.append({**row, 'classification': 'supported_landing_alias' if proof else 'unresolved_scope',
                          'scope_evidence_url': proof})
    new = []
    for name, urls in observed.items():
        parent = category_id(roots[name]); ancestors = set()
        for url in urls:
            ids = category_id(url).split('_')
            if parent in ids:
                ancestors.update(ids[:ids.index(parent)])
        for url, digest in urls.items():
            if url not in old_urls:
                new.append(dict(category=name, url=url, classification=classify(url, roots[name], ancestors),
                                source_snapshot_sha256=digest))
    assert len(remaining) == 80 and len({d['url'] for d in new}) == 61
    previous_plan = json.loads((base / 'step6-link-scope/bounded-plan.json').read_text())
    tested = {c['category']: category_id(c['url']) for c in previous_plan}
    plan = []
    for name in roots:
        aliases = [r for r in remaining if r['category'] == name and r['scope_evidence_url']]
        children = [r for r in new if r['category'] == name and r['classification'] == 'supported_descendant_id' and category_id(r['url']) != tested.get(name)]
        options = aliases or children
        if options:
            selected = min(options, key=lambda r: (len(category_id(r['url']).split('_')), len(r['url']), r['url']))
            plan.append(dict(category=name, url=selected['url'], required_root=roots[name],
                             scope_evidence_url=selected.get('scope_evidence_url') or selected['url'],
                             source_snapshot_sha256=selected['source_snapshot_sha256'],
                             reason='Observed landing ID matches observed descendant leaf' if aliases else 'Observed explicit descendant ID ancestry'))
    assert 0 < len(plan) <= 7
    out = base / 'step6-remaining-scope'; out.mkdir(exist_ok=True)
    summary = dict(mode='Offline review of saved live source links; no new requests',
                   original_unresolved_associations=80, original_unresolved_unique_urls=len({r['url'] for r in unresolved}),
                   remaining_classification_counts=dict(Counter(r['classification'] for r in remaining)),
                   new_unique_urls_reviewed=61, new_associations_reviewed=len(new),
                   new_classification_counts=dict(Counter(r['classification'] for r in new)),
                   test_pages_selected=len(plan), full_coverage_complete=False,
                   limit='Matching numeric category IDs support alias testing; they do not prove landing contents or exhaustive coverage. Unresolved scope stays open.')
    for name, value in [('summary.json', summary), ('remaining-decisions.json', remaining), ('new-url-decisions.json', new), ('bounded-plan.json', plan)]:
        (out / name).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(summary)); print(json.dumps(plan))


if __name__ == '__main__':
    review()
