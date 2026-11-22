"""Regression tests for VK community-token publishing and photo-token fallback."""
import os
import unittest
from unittest.mock import patch

import run


class VKPublishingTests(unittest.TestCase):
    def test_community_token_publishes_source_link_without_photo(self):
        with patch.dict(os.environ, {'VK_PHOTO_USER_TOKEN': ''}), \
             patch.object(run, 'resolve_vk_group_id', return_value='123'), \
             patch.object(run, 'vk_call', return_value={'post_id': 42}) as call:
            result = run.post_vk('News text', b'jpeg', 'https://example.com/news')
        self.assertEqual(result, '42')
        method, params = call.call_args.args
        self.assertEqual(method, 'wall.post')
        self.assertEqual(params['owner_id'], -123)
        self.assertIn('https://example.com/news', params['message'])
        self.assertIn('Источник:', params['message'])

    def test_photo_token_permission_error_falls_back_to_text(self):
        def vk_response(method, params, token=None):
            if method == 'photos.getWallUploadServer':
                raise RuntimeError('VK photos.getWallUploadServer error 27: Group authorization failed')
            return {'post_id': 43}

        with patch.dict(os.environ, {'VK_PHOTO_USER_TOKEN': 'sample-token'}), \
             patch.object(run, 'resolve_vk_group_id', return_value='123'), \
             patch.object(run, 'vk_call', side_effect=vk_response):
            result = run.post_vk('News text', b'jpeg', 'https://example.com/news')
        self.assertEqual(result, '43')

    def test_text_fallback_rejects_missing_source_link(self):
        with patch.dict(os.environ, {'VK_PHOTO_USER_TOKEN': ''}), \
             patch.object(run, 'resolve_vk_group_id', return_value='123'), \
             patch.object(run, 'vk_call') as call:
            with self.assertRaisesRegex(RuntimeError, 'verified HTTPS'):
                run.post_vk('News text', b'jpeg')
            call.assert_not_called()


class TelegramCaptionTests(unittest.TestCase):
    def test_source_link_is_added_to_caption(self):
        caption = run.telegram_caption('Новость', 'https://example.com/news')
        self.assertEqual(caption, 'Новость\n\nИсточник: https://example.com/news')

    def test_rejects_untrusted_source(self):
        with self.assertRaisesRegex(RuntimeError, 'verified HTTPS'):
            run.telegram_caption('Новость', 'http://example.com/news')

    def test_truncates_caption_over_limit_without_losing_source(self):
        caption = run.telegram_caption('Очень важная новость ' * 100, 'https://example.com/news')
        self.assertLessEqual(len(caption), 1024)
        self.assertTrue(caption.endswith('Источник: https://example.com/news'))
        self.assertIn('…', caption)

    def test_rejects_extremely_long_source_url(self):
        with self.assertRaisesRegex(RuntimeError, 'too long'):
            run.telegram_caption('Новость', 'https://example.com/' + 'x' * 1000)

    def test_telegram_photo_uses_source_caption(self):
        from unittest.mock import Mock
        response = Mock(status_code=200)
        response.json.return_value = {'ok': True, 'result': {'message_id': 21}}
        with patch.dict(os.environ, {'TG_BOT_TOKEN': 'test', 'TG_CHAT_ID': '@gameqivo'}), \
             patch.object(run.HTTP, 'post', return_value=response) as post:
            message_id = run.post_telegram('Новость', b'jpeg', 'https://example.com/news')
        self.assertEqual(message_id, '21')
        self.assertIn('Источник: https://example.com/news', post.call_args.kwargs['data']['caption'])


if __name__ == '__main__':
    unittest.main()
