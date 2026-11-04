import unittest
from editorial import canonical_url, is_duplicate, validate_post

class EditorialSafetyTests(unittest.TestCase):
    def test_tracking_query(self):
        self.assertEqual(canonical_url('https://example.com/story/?utm_source=x'),
                         canonical_url('https://example.com/story'))
    def test_duplicate_url(self):
        self.assertTrue(is_duplicate('Different title', 'https://example.com/story?utm_campaign=x',
                                     [{'url':'https://example.com/story','title':'Old'}]))
    def test_duplicate_headline(self):
        self.assertTrue(is_duplicate('Major Game Update Today', 'https://a.example/1',
                                     [{'url':'https://b.example/2','title':'major game update today'}]))
    def test_distinct_story(self):
        self.assertFalse(is_duplicate('New console release', 'https://a.example/1',
                                      [{'url':'https://b.example/2','title':'PC graphics card drivers'}]))
    def test_post_validation(self):
        self.assertTrue(validate_post('Игровая студия представила обновление. Подробности опубликованы в официальном блоге разработчиков.'))
        self.assertFalse(validate_post('Подпишитесь на канал!'))

if __name__ == '__main__':
    unittest.main()
