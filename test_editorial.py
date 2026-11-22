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

    def test_hourly_limit_blocks_second_publication(self):
        now = datetime(2026, 11, 22, 9, 45, tzinfo=timezone.utc)
        posts = {'one': {'created_utc': '2026-11-22T09:17:00+00:00',
                         'vk_id': '42', 'tg_id': '21'}}
        self.assertTrue(run.published_in_current_hour(posts, now))
        self.assertFalse(run.published_in_current_hour(posts, now + timedelta(hours=1)))

    def test_hourly_limit_ignores_unpublished_records(self):
        now = datetime(2026, 11, 22, 9, 45, tzinfo=timezone.utc)
        posts = {'one': {'created_utc': '2026-11-22T09:17:00+00:00',
                         'vk_id': None, 'tg_id': None}}
        self.assertFalse(run.published_in_current_hour(posts, now))

    def test_official_sources_not_displaced_by_media(self):
        media = [{'title': f'Media {i}', 'tier': 'media',
                  'published': '2026-11-22T09:59:00+00:00'} for i in range(100)]
        official = [{'title': 'Official one', 'tier': 'official',
                     'published': '2026-11-22T09:00:00+00:00'}]
        chosen = run.select_official_candidates(media + official)
        self.assertEqual([item['title'] for item in chosen], ['Official one'])

    def test_official_selection_prefers_newer_items(self):
        items = [{'tier': 'official', 'published': f'2026-11-22T{hour:02d}:00:00+00:00'}
                 for hour in range(5)]
        chosen = run.select_official_candidates(items, limit=2)
        self.assertEqual([item['published'] for item in chosen],
                         ['2026-11-22T04:00:00+00:00', '2026-11-22T03:00:00+00:00'])

    def test_news_queue_includes_media_when_official_is_empty(self):
        now = datetime.now(timezone.utc).isoformat()
        items = [{'title': 'News', 'url': 'https://prohitech.ru/story',
                  'published': now, 'tier': 'media', 'image_url': '', 'article': ''}]
        self.assertEqual(run.ranked_news_candidates(items)[0]['url'], items[0]['url'])

    def test_news_queue_does_not_discard_lower_priority_items(self):
        now = datetime.now(timezone.utc).isoformat()
        items = [{'title': 'Story ' + str(i), 'url': 'https://example.com/' + str(i),
                  'published': now, 'tier': 'media', 'image_url': '', 'article': ''}
                 for i in range(20)]
        ranked = run.ranked_news_candidates(items)
        self.assertEqual(len(ranked), 20)
        self.assertEqual({a['url'] for a in ranked}, {a['url'] for a in items})

    def test_queue_prefers_higher_priority_official_news(self):
        now = datetime.now(timezone.utc).isoformat()
        items = [
            {'title': 'Small item', 'url': 'https://media.example/1',
             'tier': 'media', 'published': now, 'article': '', 'image_url': ''},
            {'title': 'Major game launch update', 'url': 'https://official.example/1',
             'tier': 'official', 'published': now, 'article': '', 'image_url': ''},
        ]
        self.assertEqual(run.ranked_news_candidates(items)[0]['tier'], 'official')

    def test_rss_summary_fallback_when_article_fetch_fails(self):
        item = {'title': 'Update', 'url': 'https://example.com/news',
                'domain': 'example.com', 'summary': 'Confirmed facts. ' * 20}
        with patch.object(run.HTTP, 'get', side_effect=TimeoutError('blocked')):
            article = run.get_article(item)
        self.assertIsNotNone(article)
        self.assertEqual(article['content_origin'], 'rss')
        self.assertEqual(article['image_url'], '')

    def test_short_rss_summary_cannot_be_used_as_article(self):
        item = {'title': 'Update', 'url': 'https://example.com/news',
                'domain': 'example.com', 'summary': 'Not enough information'}
        with patch.object(run.HTTP, 'get', side_effect=TimeoutError('blocked')):
            self.assertIsNone(run.get_article(item))

    def test_evergreen_posts_are_distinct_and_nonempty(self):
        self.assertGreaterEqual(len(run.EVERGREEN_POSTS), 7)
        self.assertEqual(len(set(run.EVERGREEN_POSTS)), len(run.EVERGREEN_POSTS))
        self.assertTrue(all(len(text) >= 80 for text in run.EVERGREEN_POSTS))

    def test_pending_evergreen_detects_partial_crosspost(self):
        posts = {'evergreen-1': {'kind': 'evergreen', 'vk_id': '4', 'tg_id': None,
                                 'created_utc': datetime.now(timezone.utc).isoformat()}}
        self.assertTrue(run.pending_evergreen(posts))
        posts['evergreen-1']['tg_id'] = '8'
        self.assertFalse(run.pending_evergreen(posts))

    def test_evergreen_hourly_cap_does_not_call_publishers(self):
        now = datetime.now(timezone.utc)
        state = {'posts': {'already': {'created_utc': now.isoformat(),
                                     'vk_id': '42', 'tg_id': '8'}}}
        with patch.object(run, 'save_state') as save, \
             patch.object(run, 'resolve_vk_group_id') as resolve:
            self.assertEqual(run.publish_evergreen(state), 0)
        save.assert_not_called()
        resolve.assert_not_called()

    def test_stale_evergreen_does_not_block_new_news(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=26)).isoformat()
        posts = {'old': {'kind': 'evergreen', 'created_utc': old,
                         'vk_id': '1', 'tg_id': None}}
        self.assertFalse(run.pending_evergreen(posts))

    def test_telegram_text_news_fallback(self):
        from unittest.mock import Mock
        response = Mock(status_code=200)
        response.json.return_value = {'ok': True, 'result': {'message_id': 123}}
        with patch.object(run, 'required', side_effect=lambda k: k), \
             patch.object(run.HTTP, 'post', return_value=response) as post:
            self.assertEqual(run.post_telegram('News', None, 'https://example.com/news'), '123')
        self.assertTrue(post.call_args.args[0].endswith('/sendMessage'))
        self.assertIn('Источник:', post.call_args.kwargs['data']['text'])

    def test_partial_news_is_resumed_before_pending_tip(self):
        now = datetime.now(timezone.utc).isoformat()
        state = {'posts': {
            'tip': {'kind': 'evergreen', 'created_utc': now, 'vk_id': '3', 'tg_id': None},
            'news': {'url': 'https://example.com/story', 'image_url': '',
                     'text': 'Verified article text', 'created_utc': now,
                     'vk_id': '5', 'tg_id': None},
        }}
        with patch.object(run, 'DRY_RUN', False), \
             patch.object(run, 'load_state', return_value=state), \
             patch.object(run, 'required', side_effect=lambda k: k), \
             patch.object(run, 'ai_client', return_value=object()), \
             patch.dict(run.os.environ, {'GEMINI_API_KEY': 'test'}, clear=False), \
             patch.object(run, 'publish_evergreen') as evergreen, \
             patch.object(run, 'post_telegram', return_value='77') as telegram, \
             patch.object(run, 'save_state'):
            self.assertEqual(run.run(), 0)
        evergreen.assert_not_called()
        telegram.assert_called_once()
        self.assertEqual(state['posts']['news']['tg_id'], '77')

    def test_domain_validation(self):
        self.assertTrue(run.one_domain('https://blog.playstation.com/a', 'blog.playstation.com'))
        self.assertFalse(run.one_domain('https://blog.playstation.com.evil.example/a', 'blog.playstation.com'))

    def test_russian_tech_sources_registered(self):
        sources = {source[0]: source for source in run.SOURCES}
        self.assertEqual(sources['Hardwareluxx Russia'][2], 'hardwareluxx.ru')
        self.assertEqual(sources['ProHiTech'][2], 'prohitech.ru')
        self.assertEqual(sources['Hardwareluxx Russia'][3], 'media')
        self.assertEqual(sources['ProHiTech'][3], 'media')

    def test_source_tiers(self):
        self.assertTrue(all(s[3] in ('official', 'media') for s in run.SOURCES))


if __name__ == '__main__':
    unittest.main()
