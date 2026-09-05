from video_pipeline.providers.libtv import _extract_media_urls


def test_extract_media_urls():
    text = "done https://cdn.example.com/a.mp4 and https://x.test/b.PNG extra"
    urls = _extract_media_urls(text)
    assert urls == ["https://cdn.example.com/a.mp4", "https://x.test/b.PNG"]
