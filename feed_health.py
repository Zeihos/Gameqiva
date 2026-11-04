"""Concurrent source diagnostics; no credentials or posting."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import calendar
import feedparser
import requests
from urllib.parse import urlparse
from sources import SOURCES

def inspect_source(source, hours=24):
    name, url, domain, tier, category = source
    try:
        r = requests.get(url, timeout=(5, 12), headers={'User-Agent':'GAMEQIVA-NewsBot/2.0'})
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        fresh = 0
        valid_links = 0
        for e in feed.entries[:50]:
            link = e.get('link', '').strip()
            parsed_link = urlparse(link)
            host = parsed_link.hostname or ''
            if parsed_link.scheme != 'https' or not (host == domain or host.endswith('.' + domain)):
                continue
            valid_links += 1
            p = e.get('published_parsed') or e.get('updated_parsed')
            if p:
                timestamp = datetime.fromtimestamp(calendar.timegm(p), timezone.utc)
                if cutoff <= timestamp <= now + timedelta(minutes=10):
                    fresh += 1
        status = 'ok' if valid_links else ('invalid_links' if feed.entries else 'empty')
        return name, len(feed.entries), fresh, status
    except Exception as exc:
        return name, 0, 0, type(exc).__name__

def inspect_all(hours=24):
    results = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(inspect_source, source, hours) for source in SOURCES]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results)

if __name__ == '__main__':
    import json
    results = inspect_all()
    print(json.dumps([{'name': n, 'entries': e, 'fresh': f, 'status': s}
                      for n,e,f,s in results], ensure_ascii=False, indent=2))
    import sys
    print('Healthy feeds:', sum(status == 'ok' for _,_,_,status in results), '/', len(results), file=sys.stderr)
