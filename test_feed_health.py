import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import feed_health

def xml(link):
    stamp = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    return (f'<rss version="2.0"><channel><title>News</title>'
            f'<item><title>New update</title><link>{link}</link>'
            f'<pubDate>{stamp}</pubDate></item></channel></rss>').encode()

SOURCE = ('Test', 'https://example.com/feed', 'example.com', 'official', 'pc')

class FeedHealthTests(unittest.TestCase):
    def test_valid_https_article(self):
        with patch('feed_health.requests.get', return_value=Mock(content=xml('https://example.com/news'))):
            name, entries, fresh, status = feed_health.inspect_source(SOURCE)
        self.assertEqual((entries, fresh, status), (1, 1, 'ok'))

    def test_external_domain_is_not_healthy(self):
        with patch('feed_health.requests.get', return_value=Mock(content=xml('https://example.com.evil.org/news'))):
            name, entries, fresh, status = feed_health.inspect_source(SOURCE)
        self.assertEqual((entries, fresh, status), (1, 0, 'invalid_links'))

    def test_future_dated_article_not_fresh(self):
        future = (datetime.now(timezone.utc) + timedelta(days=2)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        payload = xml('https://example.com/news').replace(
            datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT').encode(), future.encode())
        with patch('feed_health.requests.get', return_value=Mock(content=payload)):
            _, entries, fresh, status = feed_health.inspect_source(SOURCE)
        self.assertEqual((entries, fresh, status), (1, 0, 'ok'))

    def test_http_article_is_not_healthy(self):
        with patch('feed_health.requests.get', return_value=Mock(content=xml('http://example.com/news'))):
            name, entries, fresh, status = feed_health.inspect_source(SOURCE)
        self.assertEqual(status, 'invalid_links')

if __name__ == '__main__':
    unittest.main()
