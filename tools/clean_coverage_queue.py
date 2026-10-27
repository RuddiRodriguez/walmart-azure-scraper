"""Remove definite queue pollution without deleting evidence or making live requests."""
import argparse,csv,fcntl,hashlib,json,re,sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from extract import category_id
from storage import atomic_json

ROOT=Path('data/full-coverage-20261026')
PUBLIC=Path('evidence/taxonomy-cleanup-20261027')


def in_root(root,child):
    return bool(re.search(r'(?:^|_)'+re.escape(root)+r'(?:_|$)',child))


def classify(category,key,url,scope_review,proofs,roots):
    page=int((parse_qs(urlsplit(url).query).get('page') or ['1'])[0])
    leaf=key.split('#')[0];identity=category_id(url)
    if '/browse/browse/' in urlsplit(url).path:return 'malformed_repeated_browse_path'
    if not identity:return 'missing_category_identifier'
    if not in_root(roots[category],identity):
        if proofs.get((category,leaf))=='scope_confirmed_by_response':return ''
        return 'outside_required_category_ancestry'
    if scope_review and proofs.get((category,leaf))!='scope_confirmed_by_response':return 'weak_alias_or_crosslink_unverified'
    return ''


def run(apply=False):
    ROOT.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True)
    lock=(ROOT/'worker.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    db=sqlite3.connect(ROOT/'queue.sqlite')
    roots={r['Category (Auto)']:category_id(r['URL']) for r in csv.DictReader(Path('config/categories.csv').open())}
    proofs={(c,leaf):decision for c,leaf,decision in db.execute('SELECT category,leaf,decision FROM scope_proofs')}
    rows=db.execute("SELECT category,key,url,status,reason,scope_review FROM pages WHERE status='pending'").fetchall()
    decisions=[]
    for category,key,url,status,old_reason,scope_review in rows:
        reason=classify(category,key,url,scope_review,proofs,roots)
        if reason:decisions.append((category,key,url,status,old_reason,reason))
    counts=Counter(d[-1] for d in decisions)
    before=dict(db.execute('SELECT status,count(*) FROM pages GROUP BY status'))
    backup=ROOT/'queue-before-taxonomy-cleanup-20261027.sqlite'
    if apply:
        if not backup.exists():
            copy=sqlite3.connect(backup);db.backup(copy);copy.close()
        db.execute('CREATE TABLE IF NOT EXISTS queue_cleanup(category TEXT,key TEXT,url TEXT,old_status TEXT,old_reason TEXT,new_status TEXT,new_reason TEXT,PRIMARY KEY(category,key))')
        with db:
            for category,key,url,status,old_reason,reason in decisions:
                db.execute('INSERT OR REPLACE INTO queue_cleanup VALUES (?,?,?,?,?,?,?)',(category,key,url,status,old_reason,'cross_link_excluded',reason))
                db.execute("UPDATE pages SET status='cross_link_excluded',reason=? WHERE category=? AND key=?",(reason,category,key))
    after=dict(db.execute('SELECT status,count(*) FROM pages GROUP BY status'))
    report=dict(mode='Offline queue cleanup; no retailer requests',applied=apply,pending_before=before.get('pending',0),excluded=len(decisions),pending_after=after.get('pending',0),reason_counts=dict(counts),status_before=before,status_after=after,evidence_deleted=False,backup=str(backup) if apply else '',backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest() if apply else '',queue_sha256_after=hashlib.sha256((ROOT/'queue.sqlite').read_bytes()).hexdigest())
    atomic_json(PUBLIC/('applied.json' if apply else 'dry-run.json'),report)
    db.close();lock.close();print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');run(parser.parse_args().apply)
