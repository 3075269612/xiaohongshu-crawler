from __future__ import annotations

import json
import re
from urllib.parse import urlencode, urljoin, urlparse

from bs4 import BeautifulSoup

from .models import SocialPost


XHS_BASE = "https://www.xiaohongshu.com"
NOTE_RE = re.compile(r"/(?:explore|discovery/item)/([0-9a-zA-Z]+)")
USER_RE = re.compile(r"/user/profile/([0-9a-zA-Z]+)")


def normalize_url(url: str, keep_query: bool = False) -> str:
    absolute = urljoin(XHS_BASE, url)
    parsed = urlparse(absolute)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if keep_query and parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def extract_note_urls(html: str, base_url: str = XHS_BASE) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: set[str] = set()

    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "")
        if NOTE_RE.search(href):
            urls.add(normalize_url(urljoin(base_url, href), keep_query=True))

    if not urls:
        for match in NOTE_RE.finditer(html):
            urls.add(f"{XHS_BASE}/explore/{match.group(1)}")

    return sorted(urls)


def extract_user_urls(html: str, base_url: str = XHS_BASE) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: set[str] = set()

    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "")
        match = USER_RE.search(href)
        if match:
            urls.add(f"{XHS_BASE}/user/profile/{match.group(1)}")

    return sorted(urls)


def _extract_text_by_selectors(soup: BeautifulSoup, selectors: list[str]) -> str:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return ""


def _parse_count(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        if text.endswith("万"):
            return int(float(text[:-1]) * 10000)
        return int(float(text))
    except ValueError:
        return None


def _cover_urls(cover: dict) -> list[str]:
    urls: list[str] = []
    for key in ("urlDefault", "urlPre", "url"):
        value = cover.get(key)
        if value:
            urls.append(value)
    for item in cover.get("infoList") or []:
        if isinstance(item, dict) and item.get("url"):
            urls.append(item["url"])
    return sorted(set(urls))


def _iter_profile_card_objects(html: str) -> list[dict]:
    decoder = json.JSONDecoder()
    objects: list[dict] = []
    parsed_ranges: list[tuple[int, int]] = []  # track parsed byte ranges to avoid re-parsing
    pos = 0
    needle = '"noteCard"'
    # Patterns for JSON object start: Explore feed uses {"trackId", profile uses {"id"
    start_patterns = ['{"trackId"', '{"id"']
    # Limit lookback to avoid matching massive __INITIAL_STATE__ JSON blobs (max 8 KB back)
    max_lookback = 8192
    while True:
        hit = html.find(needle, pos)
        if hit < 0:
            break
        pos = hit + len(needle)
        # Skip if this noteCard falls inside an already-parsed range
        if any(low <= hit < high for low, high in parsed_ranges):
            continue
        lookback_start = max(0, hit - max_lookback)
        start = -1
        for pattern in start_patterns:
            start = html.rfind(pattern, lookback_start, hit)
            if start >= 0:
                # Skip if this start position is inside an already-parsed range
                if any(low <= start < high for low, high in parsed_ranges):
                    start = -1
                    continue
                break
        if start < 0:
            continue
        try:
            value, end = decoder.raw_decode(html[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("noteCard"), dict):
            objects.append(value)
            parsed_ranges.append((start, start + end))
            pos = start + end
    return objects


def parse_profile_note_cards(html: str, source_url: str = "") -> list[SocialPost]:
    posts: list[SocialPost] = []
    seen: set[str] = set()
    for item in _iter_profile_card_objects(html):
        card = item.get("noteCard") or {}
        note_id = card.get("noteId") or item.get("id")
        if not note_id or note_id in seen:
            continue
        seen.add(note_id)

        xsec_token = card.get("xsecToken") or item.get("xsecToken") or ""
        query = {"xsec_source": "pc_user"}
        if xsec_token:
            query["xsec_token"] = xsec_token
        url = f"{XHS_BASE}/explore/{note_id}?{urlencode(query)}"

        user = card.get("user") or {}
        cover = card.get("cover") or {}
        interact = card.get("interactInfo") or {}
        title = card.get("displayTitle") or ""
        note_type = card.get("type") or ""

        posts.append(
            SocialPost(
                platform="xiaohongshu",
                post_id=note_id,
                url=url,
                author_id=user.get("userId", ""),
                author_name=user.get("nickname") or user.get("nickName") or "",
                title=title,
                content="",
                tags=sorted(set(re.findall(r"#([\w\u4e00-\u9fff-]+)", title))),
                image_urls=_cover_urls(cover),
                video_urls=[],
                like_count=_parse_count(interact.get("likedCount")),
                raw={
                    "source": "profile_card",
                    "source_url": source_url,
                    "xsec_token": xsec_token,
                    "type": note_type,
                    "cover_width": cover.get("width"),
                    "cover_height": cover.get("height"),
                    "sticky": interact.get("sticky"),
                },
            )
        )
    return posts


def parse_note_html(html: str, url: str) -> SocialPost:
    soup = BeautifulSoup(html, "html.parser")
    clean_url = normalize_url(url)
    note_id = ""
    match = NOTE_RE.search(clean_url)
    if match:
        note_id = match.group(1)

    title = _extract_text_by_selectors(soup, ["#detail-title", ".title", "h1"])
    if not title:
        meta_title = soup.select_one("meta[property='og:title'], meta[name='title']")
        title = meta_title.get("content", "").strip() if meta_title else ""

    content = _extract_text_by_selectors(soup, ["#detail-desc", ".desc", ".note-content", "article"])

    author_name = _extract_text_by_selectors(soup, [".author .name", ".user-name", ".nickname"])
    author_id = ""
    author_url = ""
    author_link = soup.find("a", href=USER_RE)
    if author_link and author_link.get("href"):
        author_url = normalize_url(author_link["href"])
        user_match = USER_RE.search(author_url)
        author_id = user_match.group(1) if user_match else ""

    image_urls = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src and not src.startswith("data:"):
            image_urls.append(urljoin(XHS_BASE, src))

    video_urls = []
    for video in soup.find_all("video"):
        src = video.get("src")
        if src:
            video_urls.append(urljoin(XHS_BASE, src))

    tags = sorted(set(re.findall(r"#([\w\u4e00-\u9fff-]+)", soup.get_text(" ", strip=True))))

    return SocialPost(
        platform="xiaohongshu",
        post_id=note_id or clean_url.rsplit("/", 1)[-1],
        url=clean_url,
        author_id=author_id,
        author_name=author_name,
        title=title,
        content=content,
        tags=tags,
        image_urls=sorted(set(image_urls)),
        video_urls=sorted(set(video_urls)),
        raw={"author_url": author_url},
    )


def parse_json_script_posts(html: str) -> list[dict]:
    """Best-effort extraction for embedded JSON states, useful for saved pages."""
    candidates = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.S | re.I)
    parsed: list[dict] = []
    for script in candidates:
        if "note" not in script.lower() and "explore" not in script.lower():
            continue
        for raw in re.findall(r"\{.*?\}", script, flags=re.S):
            try:
                value = json.loads(raw)
            except Exception:
                continue
            if isinstance(value, dict):
                parsed.append(value)
    return parsed

