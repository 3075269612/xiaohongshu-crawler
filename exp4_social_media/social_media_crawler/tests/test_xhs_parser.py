from social_media_crawler.src.xhs_parser import extract_note_urls, extract_user_urls, parse_note_html


SAMPLE_LIST_HTML = """
<html><body>
  <a href="/explore/abc123">note</a>
  <a href="https://www.xiaohongshu.com/user/profile/user456">author</a>
</body></html>
"""


SAMPLE_NOTE_HTML = """
<html><body>
  <h1 id="detail-title">一次城市漫步</h1>
  <div id="detail-desc">今天去了江边 #武汉 #citywalk</div>
  <a href="/user/profile/user456"><span class="nickname">小红</span></a>
  <img src="https://ci.xiaohongshu.com/image1.jpg" />
  <video src="https://sns-video.xhscdn.com/video.mp4"></video>
</body></html>
"""


def test_extract_note_urls():
    assert extract_note_urls(SAMPLE_LIST_HTML) == ["https://www.xiaohongshu.com/explore/abc123"]


def test_extract_user_urls():
    assert extract_user_urls(SAMPLE_LIST_HTML) == ["https://www.xiaohongshu.com/user/profile/user456"]


def test_parse_note_html():
    post = parse_note_html(SAMPLE_NOTE_HTML, "https://www.xiaohongshu.com/explore/abc123")
    assert post.platform == "xiaohongshu"
    assert post.post_id == "abc123"
    assert post.title == "一次城市漫步"
    assert post.has_video is True
    assert "武汉" in post.tags