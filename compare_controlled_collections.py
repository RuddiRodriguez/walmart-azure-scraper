"""Offline comparison of two source-audited bounded samples; no retailer requests."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


def product_id(row):
    return urlsplit(row['url']).path.rstrip('/').rsplit('/', 1)[-1]


def compare_rows(before, after, unavailable_before=(), unavailable_after=()):
    left = {product_id(r): r for r in before}
    right = {product_id(r): r for r in after}
    common = sorted(left.keys() & right.keys())
    price_changes, price_presence, availability, category_changes = [], [], [], []
    for key in common:
        a, b = left[key], right[key]
        old, new = a.get('sale_price') or a.get('regular_price', ''), b.get('sale_price') or b.get('regular_price', '')
        if old and new and old != new:
            price_changes.append(dict(product_id=key, before=old, after=new))
        if bool(old) != bool(new):
            price_presence.append(dict(product_id=key, before=old, after=new))
        if (key in unavailable_before) != (key in unavailable_after):
            availability.append(dict(product_id=key, unavailable_before=key in unavailable_before,
                                     unavailable_after=key in unavailable_after))
        if a.get('category') != b.get('category'):
            category_changes.append(dict(product_id=key, before=a.get('category'), after=b.get('category')))
    return dict(common_product_ids=len(common), baseline_only_ids=sorted(left.keys() - right.keys()),
                repeat_only_ids=sorted(right.keys() - left.keys()), comparable_price_pairs=sum(
                    bool(left[k].get('sale_price') or left[k].get('regular_price')) and
                    bool(right[k].get('sale_price') or right[k].get('regular_price')) for k in common),
                effective_price_changes=price_changes, local_price_presence_changes=price_presence,
                source_unavailability_changes=availability, category_assignment_changes=category_changes,
                note='Sample membership differences are not product additions/deletions; prices/stock can change. Blank prices are not treated as zero.')


def compare(baseline, repeat):
    baseline, repeat = Path(baseline), Path(repeat)
    a = json.loads((baseline / 'summary.json').read_text())
    b = json.loads((repeat / 'summary.json').read_text())
    before = json.loads((baseline / 'products.json').read_text())
    after = json.loads((repeat / 'products.json').read_text())
    preflight = json.loads((repeat / 'preflight.json').read_text())
    if hashlib.sha256((baseline / 'products.json').read_bytes()).hexdigest() != preflight['baseline_dataset_sha256']:
        raise ValueError('Frozen baseline dataset changed; comparison stopped')
    ua = {r['product_id'] for r in json.loads((baseline / 'accepted-source-audit.json').read_text()) if r['acceptance_reason'] == 'retained_unavailable'}
    ub = {r['product_id'] for r in json.loads((repeat / 'accepted-source-audit.json').read_text()) if r['acceptance_reason'] == 'retained_unavailable'}
    matches = a['source_hashes'] == b['source_hashes']
    plan_matches = (baseline / 'plan.json').read_bytes() == (repeat / 'plan.json').read_bytes()
    result = dict(mode='Offline comparison of independently audited bounded live samples, not full-catalog proof',
                  identical_collection_source=matches, identical_plan_bytes=plan_matches,
                  baseline_source_commit=a['source_commit'], repeat_source_commit=b['source_commit'],
                  both_samples_accepted=a['sample_accepted'] and b['sample_accepted'],
                  baseline_records=a['accepted_records'], repeat_records=b['accepted_records'],
                  baseline_category_counts=a['category_counts'], repeat_category_counts=b['category_counts'],
                  baseline_seconds=a['seconds'], repeat_seconds=b['seconds'],
                  runtime_difference_seconds=round(b['seconds'] - a['seconds'], 3),
                  runtime_difference_percent=round(100 * (b['seconds'] / a['seconds'] - 1), 2),
                  baseline_rejections=a['rejected_product_details'], repeat_rejections=b['rejected_product_details'],
                  baseline_exception_count=len(a['handled_failures']), repeat_exception_count=len(b['handled_failures']),
                  baseline_wrong_store_responses=a['wrong_store_observations'], repeat_wrong_store_responses=b['wrong_store_observations'],
                  baseline_unavailable=a['unavailable_successes'], repeat_unavailable=b['unavailable_successes'],
                  baseline_fields=a['sample_validation']['field_nonempty_counts'], repeat_fields=b['sample_validation']['field_nonempty_counts'],
                  baseline_requests=a['counts'], repeat_requests=b['counts'],
                  baseline_duplicate_ids=a['sample_validation']['duplicate_product_ids'], repeat_duplicate_ids=b['sample_validation']['duplicate_product_ids'],
                  full_uncapped_coverage_proven=False, repeated_full_collection_proven=False,
                  interpretation='Two accepted bounded samples support sample repeatability only; no upstream store-drift remedy or unexecuted recovery/Azure claim.',
                  **compare_rows(before, after, ua, ub))
    (repeat / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    table = '\n'.join(f'|{name}|{a["category_counts"].get(name, 0)}|{b["category_counts"].get(name, 0)}|' for name in sorted(set(a['category_counts']) | set(b['category_counts'])))
    text = f'''# Bounded repeat comparison

Same collection source: {matches}. Identical plan: {plan_matches}. Both samples accepted: {result['both_samples_accepted']}.

|Measure|Baseline|Repeat|
|---|---:|---:|
|Accepted records|{a['accepted_records']}|{b['accepted_records']}|
|Runtime seconds|{a['seconds']}|{b['seconds']}|
|Rejected responses|{sum(a['rejected_product_details'].values())}|{sum(b['rejected_product_details'].values())}|
|Exceptions|{len(a['handled_failures'])}|{len(b['handled_failures'])}|
|Unavailable retained|{a['unavailable_successes']}|{b['unavailable_successes']}|

|Category|Baseline|Repeat|
|---|---:|---:|
{table}

Common IDs: {result['common_product_ids']}. Comparable nonblank price pairs: {result['comparable_price_pairs']}.
Observed effective-price changes: {len(result['effective_price_changes'])}. Source unavailability changes:
{len(result['source_unavailability_changes'])}. Sample-only membership changes do not mean products
were created/deleted. Blank prices are not zero. Individual differences are in comparison.json.

This is bounded-sample repeatability evidence, not full uncapped collection or a proven store-drift
remedy. Offers, full scope, current-wrapper live recovery, Azure and private-pair reviewed sharing
remain separate open requirements. No client contact or submission.
'''
    (repeat / 'COMPARISON.md').write_text(text)
    print(json.dumps({k: result[k] for k in ['both_samples_accepted', 'identical_collection_source', 'identical_plan_bytes', 'baseline_records', 'repeat_records', 'common_product_ids', 'runtime_difference_percent']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--repeat', type=Path, required=True)
    args = parser.parse_args()
    compare(args.baseline, args.repeat)
