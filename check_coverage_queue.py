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
        data=json.loads(BeautifulSoup(html,'html.parser').script.string);search=data['props']['pageProps']['initialData']['searchResult'];search['catInfo']={'catId':q.category_id(url)}
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
    result=dict(passed=True,checks=checks,live_requests=0)
    folder=Path('evidence/point3-coverage-queue-20261026');folder.mkdir(exist_ok=True)
    (folder/'offline-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':check()
