"""Persistent bounded category/pagination review. Records gaps; never claims partial walk complete."""
import argparse,csv,hashlib,json,os,re,shutil,signal,sqlite3,subprocess,time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from bs4 import BeautifulSoup
from browser import open_browser,select_store,navigate,verify_banner,fetch_product
from diagnostic_capture import make_capture,safe_url
from extract import category_id,discover,next_data,product_record,promotion_fields,FINANCE
from capture_store_drift import listing_from_rendered
from scrape import next_page_url,verify_listing_store
from storage import atomic_json,page_url
from audit_queue_growth import listing_ids

CODEX=Path('/Volumes/CODEX')
EXTERNAL_DATA=CODEX/'Walmart_Scraper_Private_Evidence'
GIB=2**30
BATCH_LIMIT=2*GIB


def ensure_storage(folder,state=None):
    if not CODEX.is_mount():raise RuntimeError('CODEX evidence drive is not mounted')
    if not Path(folder).resolve().is_relative_to(EXTERNAL_DATA.resolve()):raise RuntimeError('Private evidence is not on the approved CODEX drive')
    if shutil.disk_usage('/').free<60*GIB:raise RuntimeError('Mac free space is below 60 GiB')
    if shutil.disk_usage(CODEX).free<40*GIB:raise RuntimeError('CODEX free space is below 40 GiB')
    if state and state['body_bytes']+state['native_bytes']>BATCH_LIMIT:raise RuntimeError('Batch growth reached 2 GiB')


def key(url):
    query=parse_qs(urlsplit(url).query)
    page=int((query.get('page') or ['1'])[0])
    if page<1:raise ValueError('Page number must be positive')
    return category_id(url).split('_')[-1]+'#'+str(page)


def run(folder,maximum,seconds):
    if not 1<=maximum<=80 or not 0<seconds<=5400:raise ValueError('Use at most80pages/90minutes per continuation')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    if (folder/'USER_PAUSED').exists():raise RuntimeError('Point3 paused by user; explicit resume required')
    ensure_storage(folder)
    import fcntl
    lock=(folder/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    db=sqlite3.connect(folder/'queue.sqlite')
    db.executescript('CREATE TABLE IF NOT EXISTS pages(category TEXT,key TEXT,url TEXT,status TEXT,reason TEXT,PRIMARY KEY(category,key)); CREATE TABLE IF NOT EXISTS links(category TEXT,url TEXT,parent TEXT,decision TEXT,PRIMARY KEY(category,url,parent));')
    db.execute('CREATE TABLE IF NOT EXISTS scope_proofs(category TEXT,leaf TEXT,decision TEXT,actual_id TEXT,breadcrumb TEXT,source TEXT,PRIMARY KEY(category,leaf))')
    if 'scope_review' not in {r[1] for r in db.execute('PRAGMA table_info(pages)')}:db.execute('ALTER TABLE pages ADD COLUMN scope_review INTEGER DEFAULT 0')
    db.execute('CREATE TABLE IF NOT EXISTS listing_fingerprints(category TEXT,leaf TEXT,page INTEGER,fingerprint TEXT,source TEXT,PRIMARY KEY(category,leaf,page))')
    db.execute('CREATE TABLE IF NOT EXISTS page_products(category TEXT,leaf TEXT,page INTEGER,product_id TEXT,PRIMARY KEY(category,leaf,page,product_id))')
    db.execute('CREATE TABLE IF NOT EXISTS eligible_page_products(category TEXT,leaf TEXT,page INTEGER,product_id TEXT,PRIMARY KEY(category,leaf,page,product_id))')
    db.execute('CREATE TABLE IF NOT EXISTS leaf_counts(category TEXT,leaf TEXT,reported_count INTEGER,aggregated_count INTEGER,reported_pages INTEGER,source TEXT,PRIMARY KEY(category,leaf))')
    initial_page_count=db.execute('SELECT count(*) FROM pages').fetchone()[0]
    growth=Counter();seeding=True
    roots={r['Category (Auto)']:page_url(r['URL']) for r in csv.DictReader(Path('config/categories.csv').open())}
    def add(category,url,parent):
        ids=category_id(url).split('_');scope=bool(re.search(r'(?:^|_)'+re.escape(category_id(roots[category]))+r'(?:_|$)',category_id(url)))
        excluded=bool(re.search(r'/recipes(?:/|$)|shop-all-foods|farm-animals',url,re.I))
        proof=db.execute('SELECT decision FROM scope_proofs WHERE category=? AND leaf=?',(category,category_id(url).split('_')[-1])).fetchone()
        decision='brief_exclusion' if excluded else proof[0] if proof else 'scoped_queue' if scope else 'scope_unverified'
        db.execute('INSERT OR IGNORE INTO links VALUES (?,?,?,?)',(category,page_url(url),parent,decision))
        if not excluded and category_id(url) and decision!='outside_required_ancestry':
            inserted=db.execute("INSERT OR IGNORE INTO pages(category,key,url,status,reason,scope_review) VALUES (?,?,?,'pending','',?)",(category,key(url),page_url(url),int(not scope and decision!='scope_confirmed_by_response')))
            growth[('seed_' if seeding else 'discovery_')+('new_page' if inserted.rowcount else 'already_known_page')]+=1
    def prove(category,url,decision,actual,breadcrumb,source):
        leaf=category_id(url).split('_')[-1]
        db.execute('INSERT OR REPLACE INTO scope_proofs VALUES (?,?,?,?,?,?)',(category,leaf,decision,actual,json.dumps(breadcrumb),source))
        for link, in db.execute('SELECT DISTINCT url FROM links WHERE category=?',(category,)).fetchall():
            if category_id(link).split('_')[-1]==leaf:db.execute("UPDATE links SET decision=? WHERE category=? AND url=? AND decision!='brief_exclusion'",(decision,category,link))
    for c,u in roots.items():add(c,u,'required_csv')
    ledger=json.loads(Path('evidence/point3-20261026/coverage-ledger.json').read_text())
    for n in ledger:add(n['category'],n['url'],'historically_observed_link')
    db.execute("UPDATE pages SET scope_review=0 WHERE scope_review=1 AND EXISTS (SELECT 1 FROM scope_proofs s WHERE s.category=pages.category AND s.leaf=substr(pages.key,1,instr(pages.key,'#')-1) AND s.decision='scope_confirmed_by_response')")
    db.commit();seeding=False
    batch=int(db.execute('SELECT count(*) FROM pages WHERE status!=\'pending\'').fetchone()[0])
    output=folder/f'batch-{batch:05}-{int(time.time())}';output.mkdir()
    settings=json.loads(Path('config/stores.json').read_text());settings.update(retries=1,max_page_seconds=25)
    store=settings['stores'][0]
    state=dict(started=time.monotonic(),limits=dict(product_requests=10,listing_requests=maximum,seconds=seconds,batch_bytes=BATCH_LIMIT),product_requests=0,listing_requests=0,sequence=0,body_bytes=0,native_bytes=0,body_limit_bytes=1024*2**20)
    from datetime import datetime,timezone
    result=dict(started_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_hashes={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in ['coverage_queue.py','audit_queue_growth.py','extract.py','browser.py']},scope='Listing/category coverage review only; no full product/PDP collection',pages=[],offer_observations=[],limits=state['limits'],full_coverage_complete=False)
    sb=None
    def log(event,**values):
        with (output/'events.jsonl').open('a') as f:f.write(json.dumps(dict(event=event,**values))+'\n')
    def save():
        coverage=[dict(category=c,leaf=leaf,reported_count=reported,aggregated_count=aggregated,reported_pages=pages,
                       reviewed_pages=reviewed,unique_listed_product_ids=listed,unique_eligible_product_ids=eligible,
                       reported_minus_unique_listed=reported-listed,complete=reviewed>=pages)
                  for c,leaf,reported,aggregated,pages,reviewed,listed,eligible in db.execute('''
                    SELECT l.category,l.leaf,l.reported_count,l.aggregated_count,l.reported_pages,
                           count(DISTINCT f.page),count(DISTINCT p.product_id),count(DISTINCT e.product_id)
                    FROM leaf_counts l
                    LEFT JOIN listing_fingerprints f ON f.category=l.category AND f.leaf=l.leaf
                    LEFT JOIN page_products p ON p.category=l.category AND p.leaf=l.leaf
                    LEFT JOIN eligible_page_products e ON e.category=l.category AND e.leaf=l.leaf
                    GROUP BY l.category,l.leaf ORDER BY l.category,l.leaf''')]
        result.update(queue_growth=dict(growth),new_page_identities=db.execute('SELECT count(*) FROM pages').fetchone()[0]-initial_page_count,seconds=round(time.monotonic()-state['started'],2),counts={k:state[k] for k in ['product_requests','listing_requests','sequence','body_bytes']},queue_counts=dict(db.execute('SELECT status,count(*) FROM pages GROUP BY status')),scope_counts=dict(db.execute('SELECT decision,count(*) FROM links GROUP BY decision')),coverage_reconciliation=coverage)
        atomic_json(output/'report.json',result)
    def alarm(*_):raise TimeoutError('Bounded coverage runtime reached')
    previous=signal.signal(signal.SIGALRM,alarm);signal.alarm(seconds)
    try:
        sb=open_browser();select_store(sb,store,settings,log,output)
        for _ in range(maximum):
            ensure_storage(folder,state)
            # Breadth first: next pending page from category with fewest completed pages.
            pending=db.execute("SELECT p.category,p.key,p.url,p.scope_review FROM pages p WHERE p.status='pending' ORDER BY p.scope_review,(SELECT count(*) FROM pages d WHERE d.category=p.category AND d.status!='pending'),p.rowid LIMIT 1").fetchone()
            if not pending:break
            category,identity,url,scope_review=pending;entry=dict(category=category,url=safe_url(url),status='started')
            result['pages'].append(entry);save()
            try:
                native=navigate(sb,url,settings,log);verify_banner(native,store)
                stable,prior=0,-1
                for scroll in range(20):
                    sb.scroll_down(900);sb.sleep(.4);native.decompose();native=BeautifulSoup(sb.get_page_source(),'html.parser');verify_banner(native,store)
                    count=len(native.select('[data-item-id]'));stable=stable+1 if count==prior else 0;prior=count
                    if stable>=4:break
                else:raise ValueError('Lazy loading did not settle')
                snapshot=output/f'native-{len(result["pages"])}.html';snapshot.write_bytes(str(native).encode());state['native_bytes']+=snapshot.stat().st_size;ensure_storage(folder,state)
                decisions=[];links=discover(native,roots[category],['recipes',r'shop[- ]all[- ]foods?$',r'farm[- ]animals'],current_url=url,decisions=decisions)
                native_search=next_data(native).get('searchResult');following_native=next_page_url(native,url,native_search);native.decompose()
                fetched=fetch_product(sb,url,settings,capture=make_capture(output/'captures','coverage',state,'listing'))
                ensure_storage(folder,state)
                try:
                    entry['listing_sequence']=state['sequence']
                    search=next_data(fetched).get('searchResult');following=None;candidate_count=0
                    if search:
                        actual=str((search.get('catInfo') or {}).get('catId') or ((search.get('paginationV2') or {}).get('pageProperties') or {}).get('cat_id') or '')
                        if not actual or actual.split('_')[-1]!=category_id(url).split('_')[-1]:raise ValueError('Response category identifier mismatch or missing')
                        breadcrumbs=search.get('breadCrumb') or []
                        ancestry=any(re.search(r'(?:^|_)'+re.escape(category_id(roots[category]))+r'(?:_|$)',str(value)) for value in [actual,*[b.get('id','') for b in breadcrumbs]])
                        if scope_review and not ancestry and len(breadcrumbs)<2:raise ValueError('Insufficient response ancestry to decide category scope')
                        entry.update(response_category_id=actual,breadcrumb=[{k:b[k] for k in ['id','name','url'] if k in b} for b in search.get('breadCrumb') or []])
                        if not ancestry:
                            if scope_review:
                                with db:
                                    db.execute("UPDATE pages SET status='outside_scope',reason='Retailer response ancestry outside required root' WHERE category=? AND key=?",(category,identity))
                                    prove(category,url,'outside_required_ancestry',actual,entry['breadcrumb'],str(output))
                                entry.update(status='outside_scope');save();continue
                            raise ValueError('Response category ancestry differs from required root')
                        verify_listing_store(search,store)
                        candidates,rejections,search=listing_from_rendered(snapshot,fetched,category,store);candidate_count=len(candidates)
                        for candidate in candidates:
                            text=candidate.get('text','')+' '+json.dumps(candidate['item'].get('promoData') or [])
                            signal_found=bool(re.search(r'buy\s+\d|\b\d+\s+for\s+\$|clip\s+(?:coupon|offer)|digital coupon|mix.{0,12}match',text,re.I))
                            if not signal_found or state['product_requests']>=10:continue
                            detail=fetch_product(sb,candidate['url'],settings,capture=make_capture(output/'captures','coverage',state,'product'))
                            try:
                                row,reason,product=product_record(candidate,detail,store,settings['private_labels'],'',retain_missing=True)
                                fields,unknown=promotion_fields(product)
                                visible=' '.join(detail.get_text(' ',strip=True).split())
                                descriptions=[fields[k] for k in ['volume_deals_description','digital_deals_description'] if fields[k]]
                                qualified=bool(row and not reason and not unknown and descriptions and all(' '.join(d.split()) in visible for d in descriptions))
                                result['offer_observations'].append(dict(product_id=candidate['item_id'],sequence=state['sequence'],qualified_candidate=qualified,fields=fields,reason=reason,unknown_count=len(unknown)))
                            except Exception as offer_error:
                                result['offer_observations'].append(dict(product_id=candidate['item_id'],sequence=state['sequence'],qualified_candidate=False,error_type=type(offer_error).__name__))
                                if any(w in str(offer_error).lower() for w in ['challenge','access blocked','disk reserve']):raise
                            finally:detail.decompose()
                        following=next_page_url(fetched,url,search) or following_native
                        pagination=search.get('paginationV2') or {};page=int((pagination.get('pageProperties') or {}).get('page') or 1);last=int(pagination.get('maxPage') or 1)
                        if page!=int((parse_qs(urlsplit(url).query).get('page') or ['1'])[0]):raise ValueError('Pagination response page mismatch')
                        ids=listing_ids(search)
                        all_ids=sorted({str(item['usItemId']) for stack in search.get('itemStacks',[]) for item in stack.get('items',[])
                                        if item.get('__typename')=='Product' and item.get('usItemId')})
                        reported_count=int(search.get('count') or 0);aggregated_count=int(search.get('aggregatedCount') or 0)
                        fingerprint=hashlib.sha256(json.dumps(ids).encode()).hexdigest() if ids else None
                        duplicate=db.execute('SELECT page,source FROM listing_fingerprints WHERE category=? AND leaf=? AND fingerprint=? AND page!=?',(category,actual,fingerprint,page)).fetchone() if fingerprint else None
                        if duplicate:
                            entry.update(repeated_listing_of_page=duplicate[0],repeated_listing_source=duplicate[1])
                            raise ValueError('Repeated product set on a different page; pagination branch requires review')
                        if fingerprint:
                            with db:
                                db.execute('INSERT OR REPLACE INTO listing_fingerprints VALUES (?,?,?,?,?)',(category,actual,page,fingerprint,str(output)))
                                db.executemany('INSERT OR IGNORE INTO page_products VALUES (?,?,?,?)',[(category,actual,page,key) for key in all_ids])
                                db.executemany('INSERT OR IGNORE INTO eligible_page_products VALUES (?,?,?,?)',[(category,actual,page,key) for key in ids])
                                db.execute('INSERT OR REPLACE INTO leaf_counts VALUES (?,?,?,?,?,?)',(category,actual,reported_count,aggregated_count,last,str(output)))
                        if page<last and not following:raise ValueError('Missing observed next-page control')
                        entry.update(page=page,reported_last_page=last,reported_count=reported_count,aggregated_count=aggregated_count,
                                     unique_listed_product_ids=len(all_ids),unique_eligible_product_ids=len(ids),
                                     listed_product_ids=all_ids,eligible_product_ids=ids,listing_rejections=dict(Counter(r['reason'] for r in rejections)))
                    elif not links:raise ValueError('Neither verified product listing nor child navigation; not legitimate empty category')
                finally:fetched.decompose()
                with db:
                    for link in links:
                        if scope_review and not search:
                            db.execute('INSERT OR IGNORE INTO links VALUES (?,?,?,?)',(category,page_url(link),url,'parent_scope_unverified'))
                        else:add(category,link,url)
                    if following:add(category,following,url)
                    db.execute("UPDATE pages SET status=?,reason='' WHERE category=? AND key=?",('navigation_scope_unverified' if scope_review and not search else 'reviewed',category,identity))
                    if search:prove(category,url,'scope_confirmed_by_response',actual,entry['breadcrumb'],str(output))
                entry.update(status='navigation_scope_unverified' if scope_review and not search else 'reviewed',candidate_count=candidate_count,next_page=safe_url(following) if following else None,snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),decisions=[{**d,'url':safe_url(d['url'])} for d in decisions])
            except Exception as error:
                if 'empty page title' in str(error).lower() and state['listing_requests']<maximum:
                    try:
                        probe=fetch_product(sb,url,settings,capture=make_capture(output/'captures','coverage',state,'listing'));probe.decompose()
                        entry['failure_body_probe']='Captured once; native rendering still failed, not accepted as empty'
                    except Exception as probe_error:
                        entry['failure_probe_error_type']=type(probe_error).__name__
                        if any(w in str(probe_error).lower() for w in ['challenge','access blocked','disk reserve']):raise
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
