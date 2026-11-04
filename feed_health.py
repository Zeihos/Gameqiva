"""Concurrent source diagnostics; no credentials or posting."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import calendar
import feedparser
import requests
from sources import SOURCES

def inspect_source(source, hours=24):
    name, url, domain, tier, category = source
    try:
        r = requests.get(url, timeout=(5, 12), headers={'User-Agent':'GAMEQIVA-NewsBot/2.0'})
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        fresh = 0
        for e in feed.entries[:50]:
            p = e.get('published_parsed') or e.get('updated_parsed')
            if p and datetime.fromtimestamp(calendar.timegm(p), timezone.utc) >= cutoff:
                fresh += 1
        return name, len(feed.entries), fresh, 'ok' if feed.entries else 'empty'
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
    print('Healthy feeds:', sum(s == 'ok' for _,_,_,s in results), '/', len(results))
