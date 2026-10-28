"""Write one clear client-facing progress page from saved coverage status."""
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


STATUS = Path('data/full-coverage-20261026/worker-status.json')
OUTPUT = Path('docs/CURRENT_PROGRESS.md')


def write_progress():
    status = json.loads(STATUS.read_text())
    counts = status.get('queue_counts') or {}
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    updated = datetime.now(ZoneInfo('Europe/Amsterdam')).strftime('%d %B %Y, %H:%M %Z')
    running = not status.get('finished')
    text = f"""# Current client review progress

Updated: {updated}  
Repository commit at update: `{commit}`

This is a live progress snapshot. It is not the final package. A new final tag will be created after coverage finishes and final checks pass.

Client run instructions: [simple step-by-step guide](RUN_GUIDE.md).

## Completed

1. Privacy-reviewed wrong-store and corrected-response pairs: [evidence](../evidence/response-pairs-reviewed-20261026/).
2. Rejection and unavailable-product retention trace: [evidence](../evidence/retention-step2-20261026/).
3. Latest-version recovery test: 132 products, 12 per required category, forced stop after 30 products, successful resume, no duplicates: [evidence](../evidence/latest-large-recovery-20261027/).
4. Separate latest-version repeat: 132 products, 125 common IDs, no price differences among common products: [evidence](../evidence/latest-large-repeat-20261027/).
5. Expanded genuine-offer review: 55 distinct products across 11 searches. No qualifying offer found; no example fabricated: [evidence](../evidence/expanded-offers-20261028/).

## Full coverage — {'running' if running else 'stopped'}

- Reviewed pages: **{counts.get('reviewed', 0):,}**
- Pending pages: **{counts.get('pending', 0):,}**
- Failed pages: **{counts.get('failed', 0):,}**
- Navigation scope unresolved: **{counts.get('navigation_scope_unverified', 0):,}**
- Cross-links excluded: **{counts.get('cross_link_excluded', 0):,}**
- Latest saved batch: `{status.get('latest_batch', '')}`

Every completed batch is saved and pushed. Wrong-store or unsafe responses remain excluded.

## Still required before final package

1. Finish pending coverage queue or record exact remaining blockers.
2. Review failed and unresolved pages.
3. Run final source, schema, store, price, duplicate and hash checks.
4. Freeze new tag and downloadable package.
5. Update final client message with exact counts, commit and evidence paths.

Azure work is separate. No Azure execution is claimed here. Nothing has been sent or submitted to the client by this repository.
"""
    OUTPUT.write_text(text)
    print(json.dumps({'output': str(OUTPUT), 'updated': updated, 'counts': counts}))


if __name__ == '__main__':
    write_progress()
