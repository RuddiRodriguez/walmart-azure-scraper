"""Store-scoped observation history. No expiry or deletion of retained products."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from storage import atomic_json

PRICE_FIELDS = ['regular_price', 'sale_price', 'volume_deals_description', 'volume_deals_price',
                'digital_deals_description', 'digital_deals_price', 'ppm']


def product_state(candidate, product, store, known=False, reason=''):
    if reason == 'retained_price_evidence_missing':
        return 'price_evidence_missing'
    from extract import pickup
    options = [o for o in product.get('fulfillmentOptions') or []
               if o.get('type') == 'PICKUP' and o.get('locationText') == store['name']]
    eligible = known or pickup(product, store) or pickup(candidate['item'], store) or any(o.get('availabilityStatus') == 'OUT_OF_STOCK' for o in options)
    if not eligible:
        return 'assortment_unverified'
    if product.get('availabilityStatus') in ['OUT_OF_STOCK', 'UNAVAILABLE'] or any(o.get('availabilityStatus') == 'OUT_OF_STOCK' for o in options):
        return 'confirmed_unavailable'
    if not pickup(product, store):
        return 'confirmed_no_pickup_offer' if any(o.get('availabilityStatus') in ['NOT_AVAILABLE', 'UNAVAILABLE'] for o in options) else 'pickup_evidence_missing'
    if product.get('availabilityStatus') not in ['IN_STOCK', 'AVAILABLE']:
        return 'availability_evidence_missing'
    return 'available'


def connect(path, store):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS catalog_meta (id TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS observations (
            product_id TEXT, observed_utc TEXT, source TEXT, state TEXT, eligible INTEGER, record TEXT,
            PRIMARY KEY(product_id, observed_utc, source));
        CREATE TABLE IF NOT EXISTS current_products (
            product_id TEXT PRIMARY KEY, observed_utc TEXT, source TEXT, state TEXT, eligible INTEGER, record TEXT);
    ''')
    signature = json.dumps({k:store[k] for k in ['id','zip','name','address']}, sort_keys=True)
    previous = db.execute("SELECT value FROM catalog_meta WHERE id='store'").fetchone()
    if previous and previous[0] != signature:
        db.close()
        raise ValueError('Retention catalog store context differs')
    db.execute("INSERT OR IGNORE INTO catalog_meta VALUES ('store',?)", (signature,))
    db.commit()
    return db


def known_assortment(db, key):
    return db.execute('SELECT 1 FROM observations WHERE product_id=? AND eligible=1 LIMIT 1', (key,)).fetchone() is not None


def observe(db, key, row, state, source, observed_utc, eligible):
    if datetime.fromisoformat(observed_utc).tzinfo is None:
        raise ValueError('Observation date requires timezone')
    if row is not None:
        row = {**row, 'crawl_date':observed_utc}
    values = (key, observed_utc, source, state, int(eligible), json.dumps(row))
    with db:
        db.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?)', values)
        prior = db.execute('SELECT observed_utc FROM current_products WHERE product_id=?', (key,)).fetchone()
        # Missing/invalid responses are archived but cannot replace a previous good observation.
        if row is not None and (not prior or datetime.fromisoformat(observed_utc) >= datetime.fromisoformat(prior[0])):
            db.execute('INSERT OR REPLACE INTO current_products VALUES (?,?,?,?,?,?)', values)
    return row



def seed_previous(db, rows, store, source):
    """Carry a previously validated store export without inventing new observation dates."""
    from extract import FIELDS
    from urllib.parse import urlsplit
    for row in rows:
        if list(row) != FIELDS or not all(isinstance(v,str) for v in row.values()):
            raise ValueError('Prior export schema mismatch')
        if (row['zipcode'],row['store_name'],row['store_location']) != (store['zip'],store['name'],store['address']):
            raise ValueError('Prior export store mismatch')
        parts=urlsplit(row['url']);key=parts.path.rstrip('/').rsplit('/',1)[-1]
        if parts.hostname!='www.walmart.com' or not key.isdigit():
            raise ValueError('Prior export product identity mismatch')
        state='carried_prior_observation'  # Do not infer current availability from old price or blank.
        observe(db,key,row,state,source,row['crawl_date'],True)


def export(db, folder):
    folder = Path(folder)
    rows, pending, states = [], [], []
    for key, date, source, state, eligible, record in db.execute('SELECT * FROM current_products ORDER BY product_id'):
        row = json.loads(record)
        (rows if eligible else pending).append(row)
        states.append(dict(product_id=key, observed_utc=date, source=source, state=state, assortment_confirmed=bool(eligible)))
    history = [dict(product_id=key, observed_utc=date, source=source, state=state, assortment_confirmed=bool(eligible), record=json.loads(record))
               for key,date,source,state,eligible,record in db.execute('SELECT * FROM observations ORDER BY observed_utc,product_id,source')]
    atomic_json(folder/'retained-products.json', rows)
    atomic_json(folder/'assortment-review.json', pending)
    atomic_json(folder/'retention-status.json', states)
    atomic_json(folder/'observation-history.json', history)
    return dict(eligible_records=len(rows), assortment_unverified=len(pending), observations=len(history), expiration_policy='No expiry or automatic deletion; dates never refreshed by export')
