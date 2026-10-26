"""Offline retention tests; synthetic cases never count as live evidence."""
import copy
import json
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from extract import FIELDS, product_record
import retention
from validate import validate


def check():
    settings=json.loads(Path('config/stores.json').read_text());store=settings['stores'][0]
    source=json.loads(Path('evidence/source-records.json').read_text())[0]
    checks=[]
    def verify(name, condition):
        assert condition,name
        checks.append(name)
    def parse(product, candidate=None, known=False):
        soup=BeautifulSoup('<script id="__NEXT_DATA__"></script>','html.parser')
        soup.script.string=json.dumps({'props':{'pageProps':{'initialData':{'data':{'product':product}}}}})
        return product_record(candidate or source['candidate'],soup,store,settings['private_labels'],'',retain_missing=True,known_store_assortment=known)
    product=copy.deepcopy(source['product']);candidate=copy.deepcopy(source['candidate'])
    row,reason,_=parse(product)
    verify('normal supported price preserved',bool(row and row['regular_price'] and reason==''))
    candidate['price_text']='';missing,reason,_=parse(product,candidate)
    verify('missing listing price retains product',bool(missing and reason=='retained_price_evidence_missing'))
    verify('unsupported prices and PPM blank',all(missing[k]=='' for k in retention.PRICE_FIELDS))
    changed=copy.deepcopy(product);changed['priceInfo']['currentPrice']['price']=99999
    mismatch,reason,_=parse(changed)
    verify('price conflict retains identity with blank prices',bool(mismatch and reason=='retained_price_evidence_missing' and not mismatch['regular_price']))
    unavailable=copy.deepcopy(product);unavailable['availabilityStatus']='OUT_OF_STOCK'
    unavailable['fulfillmentSummary']=[]
    unavailable['fulfillmentOptions']=[dict(type='PICKUP',locationText=store['name'],availabilityStatus='NOT_AVAILABLE')]
    out,reason,_=parse(unavailable)
    verify('eligible unavailable retained without offer',bool(out and reason=='retained_unavailable'))
    verify('unavailable current prices never copied from shipping',all(out[k]=='' for k in retention.PRICE_FIELDS))
    absent_seller=copy.deepcopy(unavailable);absent_seller['sellerName']=absent_seller['sellerDisplayName']=None
    seller_row,seller_reason,_=parse(absent_seller)
    verify('unavailable omitted seller uses proven listing retailer',bool(seller_row and seller_reason=='retained_unavailable'))
    marketplace=copy.deepcopy(unavailable);marketplace['sellerName']='Other seller'
    verify('explicit third-party seller remains excluded',parse(marketplace)[1]=='marketplace')
    verify('unchanged required schema',list(out)==FIELDS and all(isinstance(v,str) for v in out.values()))
    unknown=copy.deepcopy(product);unknown['fulfillmentSummary']=[];unknown['fulfillmentOptions']=[]
    c=copy.deepcopy(source['candidate']);c['item']['fulfillmentSummary']=[]
    pending,reason,_=parse(unknown,c)
    verify('no local assortment proof remains unresolved',bool(pending and reason=='retained_assortment_unverified'))
    verify('unresolved assortment is not called unavailable',retention.product_state(c,unknown,store)=='assortment_unverified')
    prior,reason,_=parse(unknown,c,True)
    verify('known assortment survives missing pickup evidence',bool(prior and reason=='retained_pickup_evidence_missing'))
    local=copy.deepcopy(unknown);local['fulfillmentOptions']=[dict(type='PICKUP',locationText=store['name'],availabilityStatus='NOT_AVAILABLE')]
    verify('known local no-offer distinguished from absent evidence',retention.product_state(c,local,store,True)=='confirmed_no_pickup_offer')
    for field in ['store','zip','identity']:
        bad=copy.deepcopy(product)
        if field=='store':bad['location']['pickupLocation']['storeId']='3081'
        if field=='zip':bad['location']['postalCode']='99999'
        if field=='identity':bad['usItemId']='999999'
        try:parse(bad)
        except ValueError:verify('wrong '+field+' cannot create local row',True)
        else:raise AssertionError(field)
    verify('blank-price eligible row validates without false unavailable label',validate([missing],[missing['category']],store,{**settings,'minimum_records':1},0,0,0,unknown_price_urls={missing['url']})['passed'])
    verify('blank-price requires explicit evidence allowance',not validate([missing],[missing['category']],store,{**settings,'minimum_records':1},0,0,0)['passed'])
    with tempfile.TemporaryDirectory(dir='data') as folder:
        path=Path(folder)/'catalog.sqlite';db=retention.connect(path,store);key=source['candidate']['item_id']
        original=retention.observe(db,key,row,'available','first','2020-01-01T10:00:00+00:00',True)
        retention.observe(db,key,out,'confirmed_unavailable','second','2020-01-02T10:00:00+00:00',True)
        retention.observe(db,'222',pending,'assortment_unverified','second','2020-01-02T10:00:00+00:00',False)
        retention.observe(db,key,None,'wrong_store_context','third','2020-01-03T10:00:00+00:00',False)
        retention.observe(db,key,out,'confirmed_unavailable','second','2020-01-02T10:00:00+00:00',True)
        db.close();db=retention.connect(path,store)
        stats=retention.export(db,Path(folder)/'export')
        kept=json.loads((Path(folder)/'export/retained-products.json').read_text());history=json.loads((Path(folder)/'export/observation-history.json').read_text())
        verify('unavailable retained indefinitely after reopen',stats['eligible_records']==1 and kept[0]['crawl_date']=='2020-01-02T10:00:00+00:00')
        verify('history preserves original price and date',history[0]['record']==original and original['crawl_date']=='2020-01-01T10:00:00+00:00')
        verify('bad response cannot overwrite last good row',kept[0]['regular_price']=='' and kept[0]['crawl_date']=='2020-01-02T10:00:00+00:00')
        verify('duplicate resume observation not appended twice',stats['observations']==4)
        verify('unverified assortment kept separately',stats['assortment_unverified']==1)
        verify('known eligibility survives no offer',retention.known_assortment(db,key))
        before=(Path(folder)/'export/retained-products.json').read_bytes();retention.export(db,Path(folder)/'export')
        verify('unseen product carried unchanged without fresh timestamp',before==(Path(folder)/'export/retained-products.json').read_bytes())
        retention.observe(db,key,missing,'available','older','2019-01-01T10:00:00+00:00',True)
        retention.export(db,Path(folder)/'export')
        verify('old replay cannot replace newer observation',before==(Path(folder)/'export/retained-products.json').read_bytes())
        retention.seed_previous(db,[original],store,'prior-publication')
        retention.export(db,Path(folder)/'export')
        verify('prior published observation imported with original date',any(v['source']=='prior-publication' and v['observed_utc']=='2020-01-01T10:00:00+00:00' for v in json.loads((Path(folder)/'export/observation-history.json').read_text())))
        verify('importing prior publication cannot overwrite newer unavailable',before==(Path(folder)/'export/retained-products.json').read_bytes())
        db.close()
        try:retention.connect(path,{**store,'id':'3081'})
        except ValueError:verify('catalog rejects different store',True)
        else:raise AssertionError('store isolation')
    result=dict(passed=True,checks=len(checks),names=checks,live_requests=0)
    Path('evidence/retention-step2-20261026/retention-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':check()
