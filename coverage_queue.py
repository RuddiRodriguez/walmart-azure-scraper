"""Persistent bounded category/pagination review. Records gaps; never claims partial walk complete."""
import argparse,csv,hashlib,json,os,re,signal,sqlite3,subprocess,time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from bs4 import BeautifulSoup
from browser import open_browser,select_store,navigate,verify_banner,fetch_product
from diagnostic_capture import make_capture,safe_url
from extract import category_id,discover,next_data
from capture_store_drift import listing_from_rendered
from scrape import next_page_url,verify_listing_store
from storage import atomic_json,page_url


def key(url):
    query=parse_qs(urlsplit(url).query)
    return category_id(url).split('_')[-1]+'#'+str((query.get('page') or ['1'])[0])


def run(folder,maximum,seconds):
    if not 1<=maximum<=80 or not 0<seconds<=5400:raise ValueError('Use at most80pages/90minutes per continuation')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(folder/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    db=sqlite3.connect(folder/'queue.sqlite')
    db.executescript('CREATE TABLE IF NOT EXISTS pages(category TEXT,key TEXT,url TEXT,status TEXT,reason TEXT,PRIMARY KEY(category,key)); CREATE TABLE IF NOT EXISTS links(category TEXT,url TEXT,parent TEXT,decision TEXT,PRIMARY KEY(category,url,parent));')
    roots={r['Category (Auto)']:page_url(r['URL']) for r in csv.DictReader(Path('config/categories.csv').open())}
    def add(category,url,parent):
        ids=category_id(url).split('_');scope=bool(re.search(r'(?:^|_)'+re.escape(category_id(roots[category]))+r'(?:_|$)',category_id(url)))
        excluded=bool(re.search(r'/recipes(?:/|$)|shop-all-foods|farm-animals',url,re.I))
        decision='brief_exclusion' if excluded else 'scoped_queue' if scope else 'scope_unverified'
        db.execute('INSERT OR IGNORE INTO links VALUES (?,?,?,?)',(category,page_url(url),parent,decision))
        if scope and not excluded:db.execute("INSERT OR IGNORE INTO pages VALUES (?,?,?,'pending','')",(category,key(url),page_url(url)))
    for c,u in roots.items():add(c,u,'required_csv')
    ledger=json.loads(Path('evidence/point3-20261026/coverage-ledger.json').read_text())
    for n in ledger:add(n['category'],n['url'],'historically_observed_link')
    db.commit()
    batch=int(db.execute('SELECT count(*) FROM pages WHERE status!=\'pending\'').fetchone()[0])
    output=folder/f'batch-{batch:05}-{int(time.time())}';output.mkdir()
    settings=json.loads(Path('config/stores.json').read_text());settings.update(retries=1,max_page_seconds=25)
    store=settings['stores'][0]
    state=dict(started=time.monotonic(),limits=dict(product_requests=1,listing_requests=maximum,seconds=seconds),product_requests=0,listing_requests=0,sequence=0,body_bytes=0,body_limit_bytes=1024*2**20)
    from datetime import datetime,timezone
    result=dict(started_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),scope='Listing/category coverage review only; no full product/PDP collection',pages=[],limits=state['limits'],full_coverage_complete=False)
    sb=None
    def log(event,**values):
        with (output/'events.jsonl').open('a') as f:f.write(json.dumps(dict(event=event,**values))+'\n')
    def save():
        result.update(seconds=round(time.monotonic()-state['started'],2),counts={k:state[k] for k in ['product_requests','listing_requests','sequence','body_bytes']},queue_counts=dict(db.execute('SELECT status,count(*) FROM pages GROUP BY status')),scope_counts=dict(db.execute('SELECT decision,count(*) FROM links GROUP BY decision')))
        atomic_json(output/'report.json',result)
    def alarm(*_):raise TimeoutError('Bounded coverage runtime reached')
    previous=signal.signal(signal.SIGALRM,alarm);signal.alarm(seconds)
    try:
        sb=open_browser();select_store(sb,store,settings,log,output)
        for _ in range(maximum):
            # Breadth first: next pending page from category with fewest completed pages.
            pending=db.execute("SELECT p.category,p.key,p.url FROM pages p WHERE p.status='pending' ORDER BY (SELECT count(*) FROM pages d WHERE d.category=p.category AND d.status!='pending'),p.rowid LIMIT 1").fetchone()
            if not pending:break
            category,identity,url=pending;entry=dict(category=category,url=safe_url(url),status='started')
            result['pages'].append(entry);save()
            try:
                native=navigate(sb,url,settings,log);verify_banner(native,store)
                stable,prior=0,-1
                for scroll in range(20):
                    sb.scroll_down(900);sb.sleep(.4);native.decompose();native=BeautifulSoup(sb.get_page_source(),'html.parser');verify_banner(native,store)
                    count=len(native.select('[data-item-id]'));stable=stable+1 if count==prior else 0;prior=count
                    if stable>=4:break
                else:raise ValueError('Lazy loading did not settle')
                snapshot=output/f'native-{len(result["pages"])}.html';snapshot.write_bytes(str(native).encode())
                decisions=[];links=discover(native,roots[category],['recipes',r'shop[- ]all[- ]foods?$',r'farm[- ]animals'],current_url=url,decisions=decisions)
                native_search=next_data(native).get('searchResult');following_native=next_page_url(native,url,native_search);native.decompose()
                fetched=fetch_product(sb,url,settings,capture=make_capture(output/'captures','coverage',state,'listing'))
                try:
                    search=next_data(fetched).get('searchResult');following=None;candidate_count=0
                    if search:
                        verify_listing_store(search,store)
                        candidates,rejections,search=listing_from_rendered(snapshot,fetched,category,store);candidate_count=len(candidates)
                        following=next_page_url(fetched,url,search) or following_native
                        pagination=search.get('paginationV2') or {};page=int((pagination.get('pageProperties') or {}).get('page') or 1);last=int(pagination.get('maxPage') or 1)
                        if page<last and not following:raise ValueError('Missing observed next-page control')
                        entry.update(page=page,reported_last_page=last,listing_rejections=dict(Counter(r['reason'] for r in rejections)))
                    elif not links:raise ValueError('Neither verified product listing nor child navigation; not legitimate empty category')
                finally:fetched.decompose()
                with db:
                    for link in links:add(category,link,url)
                    if following:add(category,following,url)
                    db.execute("UPDATE pages SET status='reviewed',reason='' WHERE category=? AND key=?",(category,identity))
                entry.update(status='reviewed',candidate_count=candidate_count,next_page=safe_url(following) if following else None,snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),decisions=[{**d,'url':safe_url(d['url'])} for d in decisions])
            except Exception as error:
                entry.update(status='failed',reason=str(error),error_type=type(error).__name__)
                with db:db.execute("UPDATE pages SET status='failed',reason=? WHERE category=? AND key=?",(str(error),category,identity))
                if any(w in str(error).lower() for w in ['challenge','access blocked','disk reserve','body budget','runtime','budget reached']):raise
            save()
    except Exception as error:result.update(stop_reason=str(error),error_type=type(error).__name__)
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,previous)
        if sb:sb.quit()
        save();db.close();lock.close()
    print(json.dumps(dict(output=str(output),**{k:result[k] for k in ['queue_counts','scope_counts','seconds']},stop_reason=result.get('stop_reason'))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('data/full-coverage-20261026'));p.add_argument('--pages',type=int,default=80);p.add_argument('--seconds',type=int,default=5400);a=p.parse_args()
    if not a.output.resolve().is_relative_to(Path('data').resolve()):raise ValueError('Private evidence stays in data/')
    os.umask(0o077);run(a.output,a.pages,a.seconds)
