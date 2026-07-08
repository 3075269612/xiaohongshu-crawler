from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path

from .models import SocialPost
from .statistics import build_stats, save_stats
from .storage import JsonlStorage


def load_config(path: str | Path = "social_media_crawler/config/config.example.json") -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class SocialMediaClient:
    def __init__(self, config: dict):
        self.config = config
        self.platform = config["platform"]
        self.queue = deque(config.get("start_urls", []))
        self.storage = JsonlStorage(config["storage"]["jsonl_path"])
        self.posts: list[SocialPost] = []
        self.failed = 0

    def run(self) -> None:
        if self.platform == "to_be_selected":
            raise SystemExit("请先在配置文件中选择 platform，并添加 start_urls。")

        while self.queue and len(self.posts) < self.config["target_post_count"]:
            url = self.queue.popleft()
            try:
                new_posts = self.fetch_user_posts(url)
                self.storage.write_many(new_posts)
                self.posts.extend(new_posts)
            except Exception:
                self.failed += 1
                raise
            time.sleep(self.config["request"]["min_interval_seconds"])

        stats = build_stats(self.platform, self.posts, visited_users=0, failed=self.failed)
        save_stats(stats, self.config["storage"]["stats_path"])

    def fetch_user_posts(self, url: str) -> list[SocialPost]:
        raise NotImplementedError("平台解析逻辑将在选择小红书或微博后实现。")


def main() -> None:
    client = SocialMediaClient(load_config())
    client.run()


if __name__ == "__main__":
    main()