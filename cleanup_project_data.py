"""Remove regenerable private drafts only after confirming intact original response bodies."""
import json,shutil
from pathlib import Path
from datetime import datetime,timezone
from archive_evidence import digest
from storage import atomic_json


def cleanup():
 root=Path('data');removed=[];skipped=[]
 for path in root.rglob('*.redaction-draft.html'):
  if path.is_symlink():continue
  prefix=path.name.removesuffix('.redaction-draft.html');meta=path.parent/(prefix+'.json')
  if not meta.exists():skipped.append(str(path));continue
  record=json.loads(meta.read_text());body=path.parent/(record.get('body_file') or 'missing')
  if not body.is_file() or not record.get('body_sha256') or digest(body)!=record['body_sha256']:skipped.append(str(path));continue
  if not record.get('redaction_draft_sha256') or digest(path)!=record['redaction_draft_sha256']:skipped.append(str(path));continue
  size=path.stat().st_size
  removed.append(dict(path=str(path),bytes=size,draft_sha256=record['redaction_draft_sha256'],original_body=str(body),original_sha256=record['body_sha256']))
  path.unlink()
 # Closed historical browser cache, not cookies/profile identity or evidence snapshots.
 cache_bytes=0
 for name in ['data/dedicated-store100-profile/Default/Cache','data/dedicated-store100-profile/Default/Code Cache']:
  p=Path(name)
  if p.is_dir():
   cache_bytes+=sum(f.stat().st_size for f in p.rglob('*') if f.is_file() and not f.is_symlink());shutil.rmtree(p)
 result=dict(time_utc=datetime.now(timezone.utc).isoformat(),removed_drafts=len(removed),removed_draft_bytes=sum(r['bytes'] for r in removed),removed_closed_browser_cache_bytes=cache_bytes,skipped=len(skipped),raw_bodies_datasets_checkpoints_approved_redactions_preserved=True,backups_untouched=True,removed=removed,skipped_paths=skipped)
 atomic_json(root/'storage-cleanup-private.json',result)
 public={k:v for k,v in result.items() if k not in ['removed','skipped_paths']};atomic_json(Path('evidence/storage-decision-20261026/cleanup-summary.json'),public);print(json.dumps(public))


if __name__=='__main__':cleanup()
