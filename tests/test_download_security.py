import unittest

from download_security import (
    is_allowed_photo_url,
    is_allowed_proxy_url,
    is_allowed_video_url,
    is_x_post_url,
    redact_url,
)


class DownloadSecurityTests(unittest.TestCase):
    def test_x_post_url_validation(self):
        self.assertTrue(is_x_post_url("https://x.com/user/status/123"))
        self.assertTrue(is_x_post_url("https://twitter.com/user/status/123/photo/1"))
        self.assertFalse(is_x_post_url("http://x.com/user/status/123"))
        self.assertFalse(is_x_post_url("https://x.com/user/status/not-a-number"))

    def test_exact_media_hosts(self):
        self.assertTrue(is_allowed_photo_url("https://pbs.twimg.com/media/abc.jpg?name=orig"))
        self.assertTrue(is_allowed_video_url("https://video.twimg.com/ext_tw_video/1/vid.mp4"))
        self.assertFalse(is_allowed_photo_url("https://pbs.twimg.com.evil.example/media/abc.jpg"))
        self.assertFalse(is_allowed_video_url("https://evil.example/video.twimg.com/vid.mp4"))

    def test_proxy_host_and_token(self):
        self.assertTrue(is_allowed_proxy_url("https://dl.snapcdn.app/get?token=header.payload.sig"))
        self.assertFalse(is_allowed_proxy_url("https://dl.snapcdn.app/other?token=header.payload.sig"))
        self.assertFalse(is_allowed_proxy_url("https://evil.example/get?token=header.payload.sig"))
        self.assertIn("token=%5Bredacted%5D", redact_url("https://dl.snapcdn.app/get?token=secret"))


if __name__ == "__main__":
    unittest.main()
