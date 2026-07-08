from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SocialPost:
    platform: str
    post_id: str
    url: str
    author_id: str = ""
    author_name: str = ""
    title: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    video_urls: list[str] = field(default_factory=list)
    comment_count: int | None = None
    like_count: int | None = None
    collect_count: int | None = None
    share_count: int | None = None
    published_at: str = ""
    crawled_at: str = field(default_factory=utc_now_iso)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def has_video(self) -> bool:
        return bool(self.video_urls) or self.raw.get("type") == "video" or self.raw.get("note_type") == "video"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["has_video"] = self.has_video
        return data


@dataclass
class CrawlStats:
    platform: str
    visited_users: int = 0
    posts: int = 0
    video_posts: int = 0
    unique_authors: int = 0
    success: int = 0
    failed: int = 0
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = ""

    @property
    def success_rate(self) -> float:
        total = self.success + self.failed
        return self.success / total if total else 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["success_rate"] = self.success_rate
        return data


