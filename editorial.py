"""Editorial safety checks for automated GAMEQIVA posts."""
import re
from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TRACKING = {'fbclid', 'gclid', 'yclid', 'ref', 'source'}

def canonical_url(url):
    p = urlsplit(url.strip())
    query = urlencode(sorted((k, v) for k, v in parse_qsl(p.query)
                             if not k.startswith('utm_') and k not in TRACKING))
    return urlunsplit((p.scheme.lower(), p.netloc.lower(),
                       p.path.rstrip('/') or '/', query, ''))

def normalize_title(title):
    return ' '.join(re.findall(r'\w+', title.casefold()))

def is_duplicate(title, url, previous, threshold=0.88):
    target = normalize_title(title)
    canonical = canonical_url(url)
    for record in previous:
        if canonical_url(record.get('url', '')) == canonical:
            return True
        old = normalize_title(record.get('title', ''))
        if old and target and SequenceMatcher(None, target, old).ratio() >= threshold:
            return True
        # Catch reordered headlines about the same event across publishers.
        a, b = set(target.split()), set(old.split())
        if len(a) >= 5 and len(b) >= 5:
            overlap = len(a & b) / min(len(a), len(b))
            if overlap >= 0.85 and len(a & b) >= 5:
                return True
    return False

def validate_post(text):
    if not text or len(text) > 800 or len(text) < 60:
        return False
    if re.search(r'https?://|#\w+', text):
        return False
    if re.search(r'(?i)(как языковая модель|я искусственный интеллект|подпишитесь на канал)', text):
        return False
    return True
