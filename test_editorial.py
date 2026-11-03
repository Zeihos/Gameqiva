import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import run


class EditorialTests(unittest.TestCase):
    def test_catalog_size(self):
        self.assertGreaterEqual(len(run.SOURCES), 50)
        self.assertEqual(len({x[1] for x in run.SOURCES}), len(run.SOURCES))

    def test_topic_key_case(self):
        self.assertEqual(run.topic_key('Major GAME Update!'), run.topic_key('major game update'))

    def test_score_bounds(self):
        item = {'title':'Game launch and update', 'published':datetime.now(timezone.utc).isoformat(),
                'tier':'official', 'image_url':'https://example.com/a.jpg', 'article':'x'*1500}
        self.assertTrue(0 <= run.importance_score(item) <= 100)

    def test_domain_validation(self):
        self.assertTrue(run.one_domain('https://blog.playstation.com/a', 'blog.playstation.com'))
        self.assertFalse(run.one_domain('https://blog.playstation.com.evil.example/a', 'blog.playstation.com'))

    def test_source_tiers(self):
        self.assertTrue(all(s[3] in ('official', 'media') for s in run.SOURCES))


if __name__ == '__main__':
    unittest.main()
