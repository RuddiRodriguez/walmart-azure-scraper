"""Export committed live unavailable records without changing the running checkpoint."""
import argparse
import json
import shutil
import sqlite3
from pathlib import Path
from tools.export_run_evidence import PRODUCT_FIELDS


def export(run, destination):
    destination.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f'file:{run / "checkpoint.sqlite"}?mode=ro', uri=True)
    selected = db.execute("SELECT records.id,records.data FROM records JOIN candidates USING(id) WHERE candidates.reason='retained_unavailable' ORDER BY records.id").fetchall()
    db.close()
    rows, sources = [], []
    for key, raw in selected:
        rows.append(json.loads(raw))
        source = json.loads((run / 'sources' / (key + '.json')).read_text())
        sources.append({'candidate':source['candidate'], 'product':{key:source['product'].get(key) for key in PRODUCT_FIELDS},
                        'specifications':source.get('specifications'), 'reason':source['reason']})
    (destination/'products.json').write_text(json.dumps(rows,indent=2)+'\n')
    (destination/'source-records.json').write_text(json.dumps(sources,indent=2)+'\n')
    (destination/'scope.json').write_text(json.dumps({'mode':'committed records from a fresh live listing-to-detail crawl', 'records':len(rows), 'run':run.name,
        'limit':'Unavailable subset only; not a complete run or category coverage claim.'},indent=2)+'\n')
    for name in ['selected-store.json','selected-store.png']:
        if (run/name).exists():shutil.copy2(run/name,destination/name)
    print('Exported',len(rows),'genuine unavailable records')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();export(args.run,args.destination)
