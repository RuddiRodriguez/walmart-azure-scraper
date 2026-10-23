"""Measure one review scraper and stop it gracefully below a reserved free-space floor."""
import argparse
import json
import shutil
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
import psutil


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pid',type=int);parser.add_argument('run',type=Path)
    parser.add_argument('--reserve-gib',type=float,default=3)
    args=parser.parse_args();process=psutil.Process(args.pid)
    if 'scrape.py' not in process.cmdline():raise SystemExit('Selected process is not scrape.py')
    minimum=shutil.disk_usage(args.run).free/2**30
    report={'started_utc':datetime.now(timezone.utc).isoformat(),'reserve_gib':args.reserve_gib,'minimum_free_gib':minimum,'triggered':False}
    try:
        while process.is_running() and process.status()!=psutil.STATUS_ZOMBIE:
            free=shutil.disk_usage(args.run).free/2**30;minimum=min(minimum,free)
            now=datetime.now(timezone.utc).isoformat()
            children_rss=0
            for child in process.children(recursive=True):
                try:children_rss+=child.memory_info().rss
                except psutil.NoSuchProcess:pass
            sample={'time_utc':now,'free_disk_gib':round(free,3),'system_swap_gib':round(psutil.swap_memory().used/2**30,3),
                    'python_rss_mib':round(process.memory_info().rss/2**20),'children_rss_mib':round(children_rss/2**20)}
            with (args.run/'resource-samples.jsonl').open('a') as stream:stream.write(json.dumps(sample)+'\n')
            report.update(checked_utc=now,minimum_free_gib=round(minimum,3))
            if free<args.reserve_gib:
                if 'scrape.py' not in process.cmdline():raise SystemExit('Process identity changed')
                report.update(triggered=True,reason='Free disk space below reserved floor')
                process.send_signal(signal.SIGINT)
                break
            (args.run/'disk-guard.json').write_text(json.dumps(report,indent=2)+'\n')
            time.sleep(15)
    except psutil.NoSuchProcess:
        pass
    report['finished_utc']=datetime.now(timezone.utc).isoformat()
    (args.run/'disk-guard.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
