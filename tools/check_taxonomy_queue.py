"""Offline checks for finite taxonomy discovery and reversible queue cleanup."""
from bs4 import BeautifulSoup
from extract import discover,descendant_id


def check():
    assert descendant_id('976759_976794','976759_976794_7433209')
    assert descendant_id('976794','976759_976794_7433209')
    assert not descendant_id('976794','976759_976787_1001407')
    html='''<main>
      <a href="/browse/food/canned-goods/976759_976794_7433209">Child</a>
      <a href="/browse/food/popcorn/976759_976787_1001407">Sibling</a>
      <a href="/cp/unrelated/123456">Unrelated</a>
    </main>'''
    decisions=[]
    links=discover(BeautifulSoup(html,'html.parser'),'https://www.walmart.com/cp/food/976759',[],current_url='https://www.walmart.com/browse/food/pantry/976759_976794',decisions=decisions)
    assert list(links)==['https://www.walmart.com/browse/food/canned-goods/976759_976794_7433209']
    assert [d['reason'] for d in decisions if d['action']=='skipped']==['not_descendant_of_current_category','outside_required_category']
    print({'passed':True,'checks':['True child retained','Sibling cross-link rejected','Unrelated category rejected']})


if __name__=='__main__':check()
