"""Short offline audit regressions using temporary copies of historical evidence."""
import copy
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import review_package


def check():
    rows = json.loads(Path('evidence/products-500.json').read_text())
    sources = json.loads(Path('evidence/source-records.json').read_text())
    checks = []
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for name in ['config/stores.json', 'config/categories.csv', 'extract.py', 'scrape.py',
                     'storage.py', 'validate.py', 'browser.py']:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(name, target)
        (root / 'evidence').mkdir()
        (root / 'evidence/SHA256SUMS.json').write_text('{}\n')
        for name in ['baseline', 'wrong source ZIP', 'wrong output ZIP', 'sale above regular price']:
            changed_rows, changed_sources = copy.deepcopy(rows), copy.deepcopy(sources)
            if name == 'wrong source ZIP':
                changed_sources[0]['product']['location']['postalCode'] = '99999'
            elif name == 'wrong output ZIP':
                changed_rows[0]['zipcode'] = '99999'
            elif name == 'sale above regular price':
                changed_rows[0].update(regular_price='1.00', sale_price='2.00')
            (root / 'evidence/products-500.json').write_text(json.dumps(changed_rows))
            (root / 'evidence/source-records.json').write_text(json.dumps(changed_sources))
            # Git labels are simulated; source and audit outputs stay in the temporary folder.
            with patch.object(review_package, '__file__', str(root / 'review_package.py')), \
                    patch('review_package.subprocess.check_output', side_effect=['offline-fixture\n', '']):
                try:
                    review_package.build()
                except SystemExit as error:
                    assert error.code == 1 and name != 'baseline'
                else:
                    assert name == 'baseline'
            report = json.loads((root / 'evidence/review-audit.json').read_text())
            assert report['passed'] == (name == 'baseline')
            checks.append(name)
    result = {'mode': 'offline historical baseline and synthetic mutations in temporary files; no network',
              'passed': True, 'checks': checks}
    Path('evidence/package-audit-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    check()
