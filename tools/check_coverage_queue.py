"""Synthetic queue/restart/skip tests; no retailer requests."""
import json,sqlite3,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from bs4 import BeautifulSoup
import coverage_queue as q


def check():
    html='<title>Fixture</title><script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'initialData':{'searchResult':{'paginationV2':{'pageProperties':{'stores':'100','facet':'fulfillment_method:Pickup','page':1},'maxPage':2}}}}}})+'</script>'
    sb=SimpleNamespace(scroll_down=lambda x:None,sleep=lambda x:None,get_page_source=lambda:html,quit=lambda:None)
    def fetch(sb,url,settings,capture):
        capture('request',url=url,attempt=1)
        data=json.loads(BeautifulSoup(html,'html.parser').script.string);search=data['props']['pageProps']['initialData']['searchResult'];search['catInfo']={'catId':q.category_id(url)};search['paginationV2']['pageProperties']['page']=int((q.parse_qs(q.urlsplit(url).query).get('page') or ['1'])[0])
        return BeautifulSoup('<title>Fixture</title><script id="__NEXT_DATA__">'+json.dumps(data)+'</script>','html.parser')
    checks=[]
    with tempfile.TemporaryDirectory(dir='data') as name:
        root=Path(name)/'queue'
        with patch.object(q,'open_browser',return_value=sb),patch.object(q,'select_store'),patch.object(q,'verify_banner'),patch.object(q,'navigate',side_effect=lambda *a:BeautifulSoup(html,'html.parser')),patch.object(q,'fetch_product',side_effect=fetch),patch.object(q,'listing_from_rendered',side_effect=lambda snapshot,page,category,store:([],[],q.next_data(page)['searchResult'])),patch.object(q,'next_page_url',return_value='https://www.walmart.com/cp/food/976759?page=2'),patch.object(q,'discover',return_value={}):
            q.run(root,2,30)
            db=sqlite3.connect(root/'queue.sqlite');assert db.execute("SELECT count(*) FROM pages WHERE status='reviewed'").fetchone()[0]==2
            assert db.execute("SELECT count(*) FROM pages WHERE category='Food' AND key='976759#2'").fetchone()[0]==1
            assert db.execute("SELECT count(*) FROM pages WHERE category='Diapering'").fetchone()[0]>0
            db.close();q.run(root,2,30)
            db=sqlite3.connect(root/'queue.sqlite');assert db.execute("SELECT count(*) FROM pages WHERE status='reviewed'").fetchone()[0]==4;db.close()
        checks+=['Composite required roots queued','Observed next page persisted','Two-page limit respected','Continuation advances without redoing committed pages']
    with tempfile.TemporaryDirectory(dir='data') as name:
        calls={'n':0}
        def navigation(*args):calls['n']+=1;raise ValueError('Empty page title; synthetic')
        with patch.object(q,'open_browser',return_value=sb),patch.object(q,'select_store'),patch.object(q,'navigate',side_effect=navigation),patch.object(q,'fetch_product',side_effect=ValueError('Synthetic empty response')):q.run(Path(name),2,30)
        db=sqlite3.connect(Path(name)/'queue.sqlite');assert db.execute("SELECT count(*) FROM pages WHERE status='failed'").fetchone()[0]==2;db.close();assert calls['n']==2
        checks+=['Bad pages logged once then next page attempted','Failed pages not counted as legitimate empty/reviewed']
    assert q.key('https://www.walmart.com/cp/x/123?page=01')==q.key('https://www.walmart.com/browse/y/4_123?page=1')
    try:q.key('https://www.walmart.com/cp/x/123?page=0')
    except ValueError:pass
    else:raise AssertionError('Zero page allowed')
    checks+=['Page aliases01and1 share one identity','Nonpositive page rejected']
    from audit_queue_growth import listing_ids
    assert listing_ids({'itemStacks':[{'items':[{'__typename':'Product','usItemId':'1','isSponsoredFlag':True},{'__typename':'Product','usItemId':'2'},{'__typename':'Product','usItemId':'2'}]}]})==['2']
    checks.append('Repeated-listing fingerprint excludes sponsored and duplicate IDs')
    original_read=Path.read_text
    def read(path,*args,**kwargs):
        if str(path)=='evidence/point3-20261026/coverage-ledger.json':return '[]'
        return original_read(path,*args,**kwargs)
    def fetch_same(sb,url,settings,capture):
        page=fetch(sb,url,settings,capture);data=json.loads(page.script.string)
        data['props']['pageProps']['initialData']['searchResult']['itemStacks']=[{'items':[{'__typename':'Product','usItemId':'123'}]}]
        page.script.string=json.dumps(data);return page
    with tempfile.TemporaryDirectory(dir='data') as name:
        with patch.object(Path,'read_text',read),patch.object(q,'open_browser',return_value=sb),patch.object(q,'select_store'),patch.object(q,'verify_banner'),patch.object(q,'navigate',side_effect=lambda *a:BeautifulSoup(html,'html.parser')),patch.object(q,'fetch_product',side_effect=fetch_same),patch.object(q,'listing_from_rendered',side_effect=lambda snapshot,page,category,store:([],[],q.next_data(page)['searchResult'])),patch.object(q,'next_page_url',return_value='https://www.walmart.com/cp/food/976759?page=2'),patch.object(q,'discover',return_value={}):
            q.run(Path(name),12,30)
        db=sqlite3.connect(Path(name)/'queue.sqlite')
        assert db.execute("SELECT count(*) FROM pages WHERE reason LIKE 'Repeated product set%'").fetchone()[0]==1
        db.close()
        checks.append('Same actual item set onpage2 stops branch and records gap')
    result=dict(passed=True,checks=checks,live_requests=0)
    folder=Path('evidence/point3-coverage-queue-20261026');folder.mkdir(exist_ok=True)
    (folder/'offline-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':check()
