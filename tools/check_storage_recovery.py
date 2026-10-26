"""Offline process-kill test of a partially written SQLite transaction."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from storage import connect


def run():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'checkpoint.sqlite'
        db = connect(path)
        with db:
            db.execute('INSERT INTO records VALUES (?,?)', ('prior', '{}'))
        db.close()
        child = subprocess.Popen([sys.executable, '-c', '''
import sqlite3,sys,time
connection=sqlite3.connect(sys.argv[1])
connection.execute('BEGIN')
connection.execute('INSERT INTO records VALUES (?,?)', ('unfinished','{}'))
print('uncommitted',flush=True)
time.sleep(60)
''', str(path)], stdout=subprocess.PIPE, text=True)
        assert child.stdout.readline().strip() == 'uncommitted'
        child.kill(); child.wait()
        db = connect(path)
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT id FROM records').fetchall() == [('prior',)]
        with db:
            db.execute('INSERT INTO records VALUES (?,?)', ('resumed', '{}'))
        assert db.execute('SELECT count(*) FROM records').fetchone()[0] == 2
        db.close()
    report = {'mode': 'offline subprocess SIGKILL inside uncommitted SQLite transaction', 'passed': True,
              'checks': ['Prior committed record retained', 'Uncommitted record rolled back', 'Database integrity OK', 'Subsequent transaction committed']}
    Path('evidence/storage-crash-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    run()
