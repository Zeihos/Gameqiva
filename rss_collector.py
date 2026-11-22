"""Bounded concurrent RSS collector for GAMEQIVA."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import calendar
import re
import requests
import feedparser
from bs4 import BeautifulSoup
from sources import SOURCES

LOW_VALUE = ('podcast', 'share of the week', 'wallpaper', 'merch', 'community spotlight', 'sweepstakes')

def fetch_source(source, cutoff):
    name, feed_url, domain, tier, category = source
    try:
        response = requests.get(feed_url, timeout=(5, 12),
                                headers={'User-Agent': 'GAMEQIVA-NewsBot/2.0'})
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        results = []
        for entry in parsed.entries[:50]:
            title = re.sub(r'\s+', ' ', entry.get('title', '')).strip()
            link = entry.get('link', '').strip()
            host = urlparse(link).hostname or ''
            if not title or urlparse(link).scheme != 'https':
                continue
            if host != domain and not host.endswith('.' + domain):
                continue
            if any(term in title.casefold() for term in LOW_VALUE):
                continue
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            if not published:
                continue
            timestamp = datetime.fromtimestamp(calendar.timegm(published), tz=timezone.utc)
            if not cutoff <= timestamp <= datetime.now(timezone.utc) + timedelta(minutes=10):
                continue
            summary_html = entry.get('summary', '') or ''
            summary_soup = BeautifulSoup(summary_html[:12000], 'html.parser')
            for unsafe in summary_soup.find_all(['script', 'style']):
                unsafe.decompose()
            summary = summary_soup.get_text(' ', strip=True)
            summary = re.sub(r'\s+', ' ', summary)
            summary = re.sub(r'\s+([.,!?;:])', r'\1', summary)[:2500]
            results.append({'url': link, 'title': title, 'summary': summary, 'publisher': name,
                            'published': timestamp.isoformat(), 'domain': domain,
                            'tier': tier, 'category': category})
        print(f'[FEED] {name}: {len(parsed.entries)} entries, {len(results)} fresh')
        return results
    except Exception as exc:
        print(f'[WARN] {name} unavailable: {type(exc).__name__}')
        return []

def fetch_candidates_parallel(hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    found = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        jobs = [executor.submit(fetch_source, source, cutoff) for source in SOURCES]
        for future in as_completed(jobs):
            for item in future.result():
                found[item['url']] = item
    print(f'[INFO] Checked {len(SOURCES)} feeds, found {len(found)} unique fresh items')
    return list(found.values())
