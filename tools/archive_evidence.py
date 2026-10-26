"""Relocate closed private evidence to approved CODEX drive after byte-for-byte verification."""
import hashlib,json,os,shutil
from pathlib import Path
from datetime import datetime,timezone
from storage import atomic_json

VOLUME=Path('/Volumes/CODEX')
DESTINATION=VOLUME/'Walmart_Scraper_Private_Evidence'
RESERVE=4*2**30


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(2**20),b''):h.update(block)
    return h.hexdigest()


def relocate(source):
    source=Path(source)
    if not VOLUME.is_mount():raise RuntimeError('Approved CODEX drive not mounted; no substitute destination')
    if source.is_symlink():return dict(source=str(source),status='already_relocated')
    if not source.resolve().is_relative_to(Path('data').resolve()):raise ValueError('Only project data evidence may be relocated')
    relative=source.absolute().relative_to(Path('data').absolute())
    paths=list(source.rglob('*'))
    files=[p for p in paths if p.is_file() and not p.is_symlink()]
    links=[p for p in paths if p.is_symlink()]
    size=sum(p.stat().st_size for p in files)
    target=DESTINATION/relative
    if source.resolve()==target.resolve():return dict(source=str(source),destination=str(target),status='already_on_external_drive')
    if shutil.disk_usage(VOLUME).free<size+RESERVE:raise RuntimeError('CODEX reserve would fall below4GiB')
    target.mkdir(parents=True,exist_ok=True,mode=0o700)
    hashes={}
    for path in files:
        name=str(path.relative_to(source));saved=target/name;saved.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        original=digest(path)
        if not saved.exists() or digest(saved)!=original:shutil.copy2(path,saved)
        if digest(saved)!=original:raise RuntimeError('External verification failed; originals preserved')
        hashes[name]=original
    link_hashes={}
    for path in links:
        name=str(path.relative_to(source));saved=target/name;saved.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        value=os.readlink(path)
        if saved.is_symlink():
            if os.readlink(saved)!=value:raise RuntimeError('Existing link differs; originals preserved')
        elif saved.exists():raise RuntimeError('Existing file conflicts with link; originals preserved')
        else:saved.symlink_to(value,target_is_directory=path.is_dir())
        if os.readlink(saved)!=value:raise RuntimeError('Link verification failed')
        link_hashes[name]=hashlib.sha256(value.encode()).hexdigest()
    # Recheck original file inventory before removing this now redundant local copy.
    if sorted(hashes)!=sorted(str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and not p.is_symlink()):raise RuntimeError('Source changed during copy')
    if any(digest(source/name)!=value for name,value in hashes.items()):raise RuntimeError('Source bytes changed during copy')
    receipt=dict(verified_utc=datetime.now(timezone.utc).isoformat(),source=str(source),destination=str(target),files=len(files),bytes=size,sha256=hashes,symlink_sha256=link_hashes,kind='Verified relocation of private evidence, not a second independent backup')
    atomic_json(target/'.relocation-receipt.json',receipt)
    # Source is closed, explicitly selected evidence. Link keeps existing audit paths usable.
    shutil.rmtree(source)
    source.symlink_to(target,target_is_directory=True)
    if any(digest(source/name)!=value for name,value in hashes.items()):raise RuntimeError('Linked evidence verification failed')
    return dict(source=str(source),destination=str(target),files=len(files),bytes=size,status='verified_and_relocated')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);a=p.parse_args();os.umask(0o077);print(json.dumps(relocate(a.source)))
