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


if __name__ == '__main__':
    unittest.main()
