"""Synthetic relocation checks; no real external volume or backup touched."""
import tempfile,json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from tools import archive_evidence as archive
from storage import atomic_json


def check():
 checks=[]
 with tempfile.TemporaryDirectory(dir='data') as name:
  root=Path(name);volume=root/'sd';volume.mkdir();destination=volume/'archive';source=root/'closed';source.mkdir();(source/'result.json').write_text('{"genuine_fixture":true}')
  with patch.object(archive,'VOLUME',volume),patch.object(archive,'DESTINATION',destination),patch.object(Path,'is_mount',return_value=True):
   receipt=archive.relocate(source)
   assert source.is_symlink() and (source/'result.json').read_text()=='{"genuine_fixture":true}'
   assert receipt['files']==1 and Path(receipt['destination'],'.relocation-receipt.json').exists()
   assert archive.relocate(source)['status']=='already_relocated'
  checks+=['Exact contents and existing path preserved through verified link','Receipt saved before local duplicate removed','Rerun does not duplicate archived evidence']
  bad=root/'failure';bad.mkdir();(bad/'original').write_text('keep me');original_digest=archive.digest
  def mismatch(path):
   return 'intentional mismatch' if path.resolve().is_relative_to(destination.resolve()) else original_digest(path)
  with patch.object(archive,'VOLUME',volume),patch.object(archive,'DESTINATION',destination),patch.object(Path,'is_mount',return_value=True),patch.object(archive,'digest',side_effect=mismatch):
   try:archive.relocate(bad)
   except RuntimeError:pass
   else:raise AssertionError('Copy mismatch accepted')
  assert not bad.is_symlink() and (bad/'original').read_text()=='keep me';checks.append('Failed SD verification leaves originals untouched')
  with patch.object(archive,'VOLUME',volume),patch.object(Path,'is_mount',return_value=False):
   try:archive.relocate(bad)
   except RuntimeError:pass
   else:raise AssertionError('Missing SD allowed')
  checks.append('Missing mounted SD cannot create substitute destination')
  with patch.object(archive,'VOLUME',volume),patch.object(Path,'is_mount',return_value=True),patch.object(archive.shutil,'disk_usage',return_value=SimpleNamespace(free=1)):
   try:archive.relocate(bad)
   except RuntimeError:pass
   else:raise AssertionError('SD reserve ignored')
  checks.append('SD free-space reserve enforced before relocation')
 out=Path('evidence/storage-decision-20261026');out.mkdir(exist_ok=True);result=dict(mode='Synthetic local tests only; no real backup/SD settings changed',passed=True,checks=checks)
 atomic_json(out/'offline-checks.json',result);print(json.dumps(result))


if __name__=='__main__':check()
