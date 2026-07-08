from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

from .captcha_solver import CaptchaRequired, handle_captcha
from .models import SocialPost
from .statistics import build_stats, save_stats
from .storage import JsonlStorage
from .xhs_parser import parse_profile_note_cards


def load_config(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_existing_posts(path: str | Path) -> tuple[list[SocialPost], set[str]]:
    jsonl_path = Path(path)
    posts: list[SocialPost] = []
    post_ids: set[str] = set()
    if not jsonl_path.exists():
        return posts, post_ids
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        data.pop("has_video", None)
        try:
            post = SocialPost(**data)
        except TypeError:
            continue
        if post.post_id in post_ids:
            continue
        post_ids.add(post.post_id)
        posts.append(post)
    return posts, post_ids


class XiaohongshuFeedClient:
    def __init__(self, config: dict):
        self.config = config
        storage = config["storage"]
        self.storage = JsonlStorage(storage["jsonl_path"])
        self.posts, self.post_ids = load_existing_posts(storage["jsonl_path"])
        self.failed = 0
        print(
            f"[resume] loaded_posts={len(self.posts)} unique_authors={self.unique_author_count()} "
            f"videos={self.video_post_count()}",
            flush=True,
        )

    def run(self) -> None:
        try:
            from DrissionPage import ChromiumOptions, ChromiumPage
        except ImportError as exc:
            raise SystemExit("需要先安装 DrissionPage：uv add DrissionPage") from exc

        options = ChromiumOptions()
        if self.config.get("browser", {}).get("headless"):
            options.headless()
        page = ChromiumPage(options)

        feed_config = self.config.get("feed", {})
        start_url = feed_config.get("start_url", "https://www.xiaohongshu.com/explore")
        max_scrolls = int(feed_config.get("max_scrolls", 400))

        print("请在打开的浏览器中完成人工登录。", flush=True)
        print(f"[open_feed] {start_url}", flush=True)
        page.get(start_url)
        print(f"[loaded_feed] url={page.url} html={len(page.html)}", flush=True)
        time.sleep(int(self.config.get("browser", {}).get("manual_login_wait_seconds", 15)))
        self.ensure_not_blocked(page.html, start_url)

        # Parse initial page cards before scrolling
        cards = parse_profile_note_cards(page.html, source_url=start_url)
        added = self.add_posts(cards)
        if added:
            self.storage.write_many(added)
        print(
            f"[init] cards={len(cards)} added={len(added)} "
            f"posts={len(self.posts)} authors={self.unique_author_count()} videos={self.video_post_count()}",
            flush=True,
        )

        for index in range(max_scrolls):
            if self.targets_reached():
                print(f"[targets_reached] posts={len(self.posts)} authors={self.unique_author_count()}", flush=True)
                break
            print(f"[scroll] {index + 1}/{max_scrolls}", flush=True)
            try:
                page.scroll.to_bottom()
            except Exception:
                # Fallback: try JS scroll if native fails
                try:
                    page.run_js("window.scrollTo(0, document.body.scrollHeight)")
                except Exception:
                    pass
            sleep_seconds = random.uniform(
                float(self.config["request"].get("min_interval_seconds", 2)),
                float(self.config["request"].get("max_interval_seconds", 5)),
            )
            time.sleep(sleep_seconds)
            self.ensure_not_blocked(page.html, start_url)

            cards = parse_profile_note_cards(page.html, source_url=start_url)
            added = self.add_posts(cards)
            if added:
                self.storage.write_many(added)
            print(
                f"[scroll] {index + 1} cards={len(cards)} added={len(added)} "
                f"posts={len(self.posts)} authors={self.unique_author_count()} videos={self.video_post_count()}",
                flush=True,
            )

        self.write_stats()
        print(
            f"[done] posts={len(self.posts)} authors={self.unique_author_count()} "
            f"videos={self.video_post_count()} failed={self.failed}",
            flush=True,
        )

    def targets_reached(self) -> bool:
        return (
            self.unique_author_count() >= int(self.config.get("target_user_count", 0))
            and len(self.posts) >= int(self.config.get("target_post_count", 0))
            and self.video_post_count() >= int(self.config.get("target_video_post_count", 0))
        )

    def add_posts(self, posts: list[SocialPost]) -> list[SocialPost]:
        added: list[SocialPost] = []
        for post in posts:
            if post.post_id in self.post_ids:
                continue
            self.post_ids.add(post.post_id)
            self.posts.append(post)
            added.append(post)
        return added

    def unique_author_count(self) -> int:
        return len({post.author_id for post in self.posts if post.author_id})

    def video_post_count(self) -> int:
        return sum(1 for post in self.posts if post.has_video)

    @staticmethod
    def ensure_not_blocked(html: str, context: str) -> None:
        block_words = ["验证码", "异常访问", "安全验证", "请完成验证", "滑块"]
        if any(word in html for word in block_words):
            handle_captcha(context)

    def write_stats(self) -> None:
        stats = build_stats(
            "xiaohongshu",
            self.posts,
            visited_users=self.unique_author_count(),
            failed=self.failed,
        )
        save_stats(stats, self.config["storage"]["stats_path"])


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="小红书首页推荐流采集入口")
    parser.add_argument("--config", default="social_media_crawler/config/xiaohongshu.final.local.json")
    args = parser.parse_args()

    client = XiaohongshuFeedClient(load_config(args.config))
    client.run()


if __name__ == "__main__":
    main()



