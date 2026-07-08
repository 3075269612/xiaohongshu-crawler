from __future__ import annotations

import json
from pathlib import Path

from .models import CrawlStats, SocialPost, utc_now_iso


def build_stats(platform: str, posts: list[SocialPost], visited_users: int, failed: int = 0) -> CrawlStats:
    stats = CrawlStats(
        platform=platform,
        visited_users=visited_users,
        posts=len(posts),
        video_posts=sum(1 for post in posts if post.has_video),
        unique_authors=len({post.author_id for post in posts if post.author_id}),
        success=len(posts),
        failed=failed,
    )
    stats.finished_at = utc_now_iso()
    return stats


def save_stats(stats: CrawlStats, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stats.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
