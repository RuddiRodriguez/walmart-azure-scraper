"""Transactional checkpoints and atomic publication on a single VM/filesystem."""
import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def connect(path):
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS pages (
            category TEXT, url TEXT, status TEXT DEFAULT 'pending',
            raw_count INTEGER DEFAULT 0, local_count INTEGER DEFAULT 0,
            PRIMARY KEY(category, url));
        CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY, data TEXT, status TEXT DEFAULT 'pending', reason TEXT);
        CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS exclusions (reason TEXT, count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
    ''')
    return db


def metadata(db, key, value=None):
    if value is not None:
        db.execute('INSERT OR REPLACE INTO meta VALUES (?, ?)', (key, json.dumps(value)))
        db.commit()
        return value
    row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
    return json.loads(row[0]) if row else None


def page_url(url):
    """Drop navigation tracking, preserving page numbers and functional filters."""
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if key not in ['povid', 'athbdg']]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))


def product_url(url):
    """Keep product identity and functional context; drop ad and navigation tracking."""
    parts = urlsplit(url)
    allowed = ['fulfillmentIntent', 'classType']
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if key in allowed]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))


def add_pages(db, category, urls):
    db.executemany('INSERT OR IGNORE INTO pages(category,url) VALUES (?,?)', [(category, page_url(u)) for u in urls])


def save_page(db, category, url, links, candidates, rejected, raw_count):
    with db:
        add_pages(db, category, links)
        for candidate in candidates:
            inserted = db.execute('INSERT OR IGNORE INTO candidates(id,data) VALUES (?,?)',
                                  (candidate['item_id'], json.dumps(candidate)))
            if inserted.rowcount == 0:
                db.execute("INSERT INTO exclusions VALUES ('duplicate',1)")
        for reason in rejected:
            db.execute('INSERT INTO exclusions VALUES (?,1)', (reason['reason'],))
        db.execute("UPDATE pages SET status='done',raw_count=?,local_count=? WHERE category=? AND url=?",
                   (raw_count, len(candidates), category, url))


def save_product(db, candidate, record, reason):
    with db:
        if record:
            db.execute('INSERT OR REPLACE INTO records VALUES (?,?)', (candidate['item_id'], json.dumps(record)))
        db.execute("UPDATE candidates SET status='done',reason=? WHERE id=?", (reason, candidate['item_id']))


def records(db):
    return [json.loads(row[0]) for row in db.execute('SELECT data FROM records ORDER BY id')]
