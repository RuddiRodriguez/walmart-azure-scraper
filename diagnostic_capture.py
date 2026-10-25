"""Private, bounded response evidence. Never writes production output."""
import base64
import hashlib
import json
import re
import shutil
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from storage import atomic_json


SENSITIVE = re.compile(r'cookie|token|authorization|password|visitor|session|customer|device|email|phone|shippingaddress|billingaddress|contactinfo', re.I)


def safe_url(url):
    parts = urlsplit(url)
    allowed = ['fulfillmentIntent', 'classType', 'page', 'stores']
    query = [(key, value if key in allowed else '[redacted]') for key, value in parse_qsl(parts.query)]
    return urlunsplit((parts.scheme, parts.hostname or '', parts.path, urlencode(query), ''))


def redact_body(body):
    """Sharing draft only; manual privacy review remains mandatory."""
    def redact(value):
        if isinstance(value, dict):
            return {key: '[redacted]' if SENSITIVE.search(key) else redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    soup = BeautifulSoup(body.decode('utf-8', errors='replace'), 'html.parser')
    for node in soup.select('script'):
        if node.get('id') == '__NEXT_DATA__':
            node.string = json.dumps(redact(json.loads(node.string or '{}'))).replace('</', '<\\/')
        else:
            node.clear()
    for node in soup.find_all(True):
        for key, value in list(node.attrs.items()):
            if SENSITIVE.search(key) or (node.name == 'input' and key == 'value'):
                node[key] = '[redacted]'
            elif key in ['href', 'src', 'action'] and isinstance(value, str) and value.startswith('http'):
                node[key] = safe_url(value)
    return str(soup).encode('utf-8')


def make_capture(output, session, state, kind='product'):
    """One callback per request. Counters include failed attempts and diagnostic retries."""
    folder = Path(output).resolve()
    if not folder.is_relative_to(Path('data').resolve()):
        raise ValueError('Raw diagnostic evidence must stay under ignored data/')
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    record = {}

    def save():
        atomic_json(folder / (record['id'] + '.json'), record)

    def capture(event, **data):
        if event == 'request':
            limit = state['limits']['product_requests' if kind == 'product' else 'listing_requests']
            key = 'product_requests' if kind == 'product' else 'listing_requests'
            if state[key] >= limit or time.monotonic() - state['started'] >= state['limits']['seconds']:
                raise RuntimeError('Diagnostic request/runtime budget reached')
            if shutil.disk_usage(folder).free < 8 * 2**30:
                raise RuntimeError('Diagnostic disk reserve below 8 GiB')
            state[key] += 1
            state['sequence'] += 1
            record.clear()
            record.update(id=f"{session}-{state['sequence']:03}", session=session, kind=kind,
                          sequence=state['sequence'], request={**data, 'url': safe_url(data['url'])},
                          body_scope='Complete bytes exposed by Fetch after content decoding; not compressed wire bytes',
                          sharing_status='Private originals and redaction draft; manual review required before sharing')
            save()
        elif event == 'response':
            result = data['result']
            body = base64.b64decode(result['body_base64'], validate=True)
            if len(body) > 10 * 2**20 or state['body_bytes'] + len(body) > 250 * 2**20:
                raise RuntimeError('Diagnostic saved-body budget reached')
            state['body_bytes'] += len(body)
            path = folder / (record['id'] + '.body')
            path.write_bytes(body)  # Original bytes saved before any parsing/redaction.
            record.update(response={'status': result['status'], 'url': safe_url(result.get('url', '')),
                                    'redirected': result.get('redirected', False),
                                    'headers': {key: value for key, value in result.get('headers', {}).items()
                                                if key in ['date', 'age', 'cache-control', 'cache-status', 'x-cache', 'vary', 'content-type']},
                                    'received_utc': data['received_utc'], 'elapsed_seconds': data['elapsed_seconds']},
                          body_file=path.name, body_bytes=len(body), body_sha256=hashlib.sha256(body).hexdigest())
            save()
            try:
                redacted = redact_body(body)
                draft = folder / (record['id'] + '.redaction-draft.html')
                draft.write_bytes(redacted)
                record['redaction_draft_sha256'] = hashlib.sha256(redacted).hexdigest()
            except Exception as error:
                record['redaction_error'] = type(error).__name__
            save()
        elif event == 'error':
            record['error'] = data
            save()

    return capture
