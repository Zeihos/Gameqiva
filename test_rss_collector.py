import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock
import rss_collector

class RSSCollectorTests(unittest.TestCase):
    def test_feed_parsing_and_date(self):
        now = datetime.now(timezone.utc)
        stamp = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        xml = (f'<rss version="2.0"><channel><title>Test</title>'
               f'<item><title>New game update released</title>'
               f'<link>https://example.com/news/1</link><pubDate>{stamp}</pubDate></item>'
               f'</channel></rss>').encode()
        response = Mock(content=xml)
        response.raise_for_status.return_value = None
        with patch('rss_collector.requests.get', return_value=response):
            items = rss_collector.fetch_source(('Example', 'https://example.com/feed',
                                                'example.com', 'official', 'pc'),
                                               now - timedelta(hours=24))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['tier'], 'official')

    def test_sanitized_rss_summary_is_kept(self):
        now = datetime.now(timezone.utc)
        stamp = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        xml = (f'<rss version="2.0"><channel><title>Test</title>'
               f'<item><title>Game update</title><link>https://example.com/a</link>'
               f'<pubDate>{stamp}</pubDate>'
               '<description><![CDATA[<p>Confirmed update <b>details</b>.</p>'
               '<script>evil()</script>]]></description></item></channel></rss>').encode()
        with patch('rss_collector.requests.get', return_value=Mock(content=xml)):
            items = rss_collector.fetch_source(('Example', 'https://example.com/feed',
                                                'example.com', 'media', 'pc'),
                                               now - timedelta(hours=24))
        self.assertIn('Confirmed update details.', items[0]['summary'])
        self.assertNotIn('<script>', items[0]['summary'])

    def test_reject_external_domain(self):
        now = datetime.now(timezone.utc)
        stamp = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        xml = (f'<rss version="2.0"><channel><title>Test</title>'
               f'<item><title>Fake</title><link>https://example.com.evil.org/a</link>'
               f'<pubDate>{stamp}</pubDate></item></channel></rss>').encode()
        with patch('rss_collector.requests.get', return_value=Mock(content=xml)):
            items = rss_collector.fetch_source(('Example', 'https://example.com/feed',
                                                'example.com', 'official', 'pc'),
                                               now - timedelta(hours=24))
        self.assertEqual(items, [])

    def test_unavailable_feed_isolated(self):
        with patch('rss_collector.requests.get', side_effect=TimeoutError('offline')):
            items = rss_collector.fetch_source(('Example', 'https://example.com/feed',
                                                'example.com', 'official', 'pc'),
                                               datetime.now(timezone.utc) - timedelta(hours=24))
        self.assertEqual(items, [])

if __name__ == '__main__':
    unittest.main()
