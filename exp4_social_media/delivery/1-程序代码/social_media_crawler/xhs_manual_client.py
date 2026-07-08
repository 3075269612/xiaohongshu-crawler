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
from .task_queue import FileTaskQueue
from .xhs_parser import extract_note_urls, extract_user_urls, parse_profile_note_cards


def load_config(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class XiaohongshuManualClient:
    def __init__(self, config: dict):
        self.config = config
        storage = config["storage"]
        self.queue = FileTaskQueue(storage["task_queue_path"], storage["visited_users_path"])
        self.queue.push_many(config.get("start_urls", []))
        self.storage = JsonlStorage(storage["jsonl_path"])
        self.posts: list[SocialPost] = []
        self.post_ids: set[str] = set()
        self.failed = 0
        self.load_existing_posts(storage["jsonl_path"])

    def load_existing_posts(self, path: str | Path) -> None:
        jsonl_path = Path(path)
        if not jsonl_path.exists():
            return
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
            if post.post_id in self.post_ids:
                continue
            self.post_ids.add(post.post_id)
            self.posts.append(post)
        print(f"[resume] loaded_posts={len(self.posts)} visited_users={len(self.queue.visited)}", flush=True)

    def run_from_saved_html(self, html_dir: str | Path) -> None:
        html_paths = sorted(Path(html_dir).glob("*.html"))
        for path in html_paths:
            html = path.read_text(encoding="utf-8")
            posts = parse_profile_note_cards(html, source_url=str(path))
            self.add_posts(posts)
        self.storage.write_many(self.posts)
        self.write_stats(visited_users=len(self.queue.visited))

    def run_with_browser(self) -> None:
        try:
            from DrissionPage import ChromiumOptions, ChromiumPage
        except ImportError as exc:
            raise SystemExit("需要先安装 DrissionPage：uv add DrissionPage") from exc

        options = ChromiumOptions()
        if self.config.get("browser", {}).get("headless"):
            options.headless()
        page = ChromiumPage(options)

        print("请在打开的浏览器中完成人工登录。", flush=True)
        self.safe_get(page, "https://www.xiaohongshu.com")
        print(f"[home] url={page.url} html={len(page.html)}", flush=True)
        time.sleep(int(self.config.get("browser", {}).get("manual_login_wait_seconds", 60)))

        visited_users = len(self.queue.visited)
        while not self.targets_reached(visited_users):
            user_url = self.queue.pop()
            if not user_url:
                print("[queue_empty] no more user urls", flush=True)
                break
            try:
                print(f"[user] {user_url}", flush=True)
                user_posts, discovered_users = self.collect_user(page, user_url)
                added_posts = self.add_posts(user_posts)
                self.storage.write_many(added_posts)
                self.queue.push_many(discovered_users)
                self.queue.mark_visited(user_url)
                visited_users += 1
                print(
                    f"[user_done] added={len(added_posts)} total_posts={len(self.posts)} "
                    f"videos={self.video_post_count()} visited_users={visited_users} discovered_users={len(discovered_users)}",
                    flush=True,
                )
            except CaptchaRequired:
                self.failed += 1
                raise
            except Exception:
                self.failed += 1
                raise

        self.write_stats(visited_users=visited_users)
        print(f"[done] posts={len(self.posts)} videos={self.video_post_count()} users={visited_users} failed={self.failed}", flush=True)

    def targets_reached(self, visited_users: int) -> bool:
        return (
            visited_users >= int(self.config.get("target_user_count", 0))
            and len(self.posts) >= int(self.config.get("target_post_count", 0))
            and self.video_post_count() >= int(self.config.get("target_video_post_count", 0))
        )

    def video_post_count(self) -> int:
        return sum(1 for post in self.posts if post.has_video)

    def add_posts(self, posts: list[SocialPost]) -> list[SocialPost]:
        added: list[SocialPost] = []
        for post in posts:
            if post.post_id in self.post_ids:
                continue
            self.post_ids.add(post.post_id)
            self.posts.append(post)
            added.append(post)
        return added

    @staticmethod
    def safe_get(page, url: str, retry: int = 1) -> None:
        for attempt in range(retry + 1):
            try:
                page.get(url)
                return
            except Exception as exc:
                print(f"[page_get_failed] attempt={attempt + 1} url={url} error={type(exc).__name__}", flush=True)
                if attempt >= retry:
                    raise
                time.sleep(3)

    def collect_user(self, page, user_url: str) -> tuple[list[SocialPost], list[str]]:
        print(f"[open_user] {user_url}", flush=True)
        self.safe_get(page, user_url)
        print(f"[loaded_user] url={page.url} html={len(page.html)}", flush=True)
        time.sleep(int(self.config.get("browser", {}).get("page_load_wait_seconds", 5)))
        self.ensure_not_blocked(page.html, user_url)

        request = self.config["request"]
        for index in range(int(request.get("scroll_times_per_user", 12))):
            page.scroll.to_bottom()
            print(f"[scroll] {index + 1}", flush=True)
            time.sleep(float(request.get("scroll_pause_seconds", 2)))
            self.ensure_not_blocked(page.html, user_url)

        note_urls = extract_note_urls(page.html, user_url)
        discovered_users = extract_user_urls(page.html, user_url)
        posts = parse_profile_note_cards(page.html, source_url=user_url)
        print(
            f"[profile_cards] cards={len(posts)} note_links={len(note_urls)} discovered_users={len(discovered_users)}",
            flush=True,
        )
        for post in posts[:5]:
            print(f"[card] id={post.post_id} type={post.raw.get('type')} title={post.title[:30]!r}", flush=True)
        time.sleep(random.uniform(self.config["request"]["min_interval_seconds"], self.config["request"]["max_interval_seconds"]))
        return posts, discovered_users

    @staticmethod
    def ensure_not_blocked(html: str, context: str) -> None:
        block_words = ["验证码", "异常访问", "安全验证", "请完成验证", "滑块"]
        if any(word in html for word in block_words):
            handle_captcha(context)

    def write_stats(self, visited_users: int) -> None:
        stats = build_stats("xiaohongshu", self.posts, visited_users=visited_users, failed=self.failed)
        save_stats(stats, self.config["storage"]["stats_path"])


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="小红书综合实验采集入口")
    parser.add_argument("--config", default="social_media_crawler/config/xiaohongshu.example.json")
    parser.add_argument("--saved-html-dir", help="从已保存的个人主页 HTML 目录解析，适合先验证解析逻辑")
    parser.add_argument("--browser", action="store_true", help="启动浏览器进行人工登录后的低频采集")
    args = parser.parse_args()

    client = XiaohongshuManualClient(load_config(args.config))
    if args.saved_html_dir:
        client.run_from_saved_html(args.saved_html_dir)
    elif args.browser:
        client.run_with_browser()
    else:
        raise SystemExit("请指定 --saved-html-dir 或 --browser")


if __name__ == "__main__":
    main()
