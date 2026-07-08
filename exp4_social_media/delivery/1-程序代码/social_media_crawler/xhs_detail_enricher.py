from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

from .captcha_solver import handle_captcha
from .models import SocialPost
from .statistics import build_stats, save_stats
from .xhs_manual_client import load_config
from .xhs_parser import parse_note_html


def read_posts(path: str | Path) -> list[SocialPost]:
    posts: list[SocialPost] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        data.pop("has_video", None)
        posts.append(SocialPost(**data))
    return posts


def merge_post(base: SocialPost, detail: SocialPost) -> SocialPost:
    return SocialPost(
        platform=base.platform,
        post_id=base.post_id,
        url=base.url,
        author_id=base.author_id or detail.author_id,
        author_name=base.author_name or detail.author_name,
        title=detail.title or base.title,
        content=detail.content or base.content,
        tags=sorted(set(base.tags + detail.tags)),
        image_urls=sorted(set(base.image_urls + detail.image_urls)),
        video_urls=sorted(set(base.video_urls + detail.video_urls)),
        comment_count=base.comment_count or detail.comment_count,
        like_count=base.like_count or detail.like_count,
        collect_count=base.collect_count or detail.collect_count,
        share_count=base.share_count or detail.share_count,
        published_at=base.published_at or detail.published_at,
        crawled_at=base.crawled_at,
        raw={**base.raw, "detail_enriched": True, "detail_raw": detail.raw},
    )


def write_jsonl(path: str | Path, posts: list[SocialPost]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        for post in posts:
            file.write(json.dumps(post.to_dict(), ensure_ascii=False) + "\n")


def is_blocked(html: str) -> bool:
    block_words = ["验证码", "异常访问", "安全验证", "请完成验证", "滑块"]
    return any(word in html for word in block_words)


def is_unavailable_note(url: str, html: str) -> bool:
    unavailable_words = ["当前笔记暂时无法浏览", "请打开小红书App扫码查看", "你访问的页面不见了"]
    return "/404" in url or "error_code=300031" in url or any(word in html for word in unavailable_words)


def new_page():
    from DrissionPage import ChromiumOptions, ChromiumPage

    return ChromiumPage(ChromiumOptions())


def enrich_one(page, post: SocialPost, config: dict) -> SocialPost | None:
    page.get(post.url)
    time.sleep(
        random.uniform(
            float(config["request"].get("min_interval_seconds", 2)),
            float(config["request"].get("max_interval_seconds", 5)),
        )
    )
    if is_blocked(page.html):
        handle_captcha(post.url)
    if is_unavailable_note(page.url, page.html):
        print(f"[skip] unavailable {page.url}", flush=True)
        return post
    detail = parse_note_html(page.html, post.url)
    return merge_post(post, detail)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="小红书笔记详情增强采集")
    parser.add_argument("--config", default="social_media_crawler/config/xiaohongshu.final.local.json")
    parser.add_argument("--input", default="social_media_crawler/data/xhs_posts.jsonl")
    parser.add_argument("--output", default="social_media_crawler/data/xhs_posts_enriched.jsonl")
    parser.add_argument("--stats", default="social_media_crawler/data/xhs_statistics_enriched.json")
    parser.add_argument("--max", type=int, default=0, help="最多处理多少条；0 表示全部")
    parser.add_argument("--retry", type=int, default=2)
    args = parser.parse_args()

    config = load_config(args.config)
    posts = read_posts(args.input)
    limit = args.max if args.max > 0 else len(posts)

    try:
        page = new_page()
    except ImportError as exc:
        raise SystemExit("需要先安装 DrissionPage：uv add DrissionPage") from exc

    enriched: list[SocialPost] = []
    failed = 0
    processed = 0

    for index, post in enumerate(posts, start=1):
        if processed >= limit:
            enriched.extend(posts[index - 1 :])
            break
        if post.raw.get("detail_enriched"):
            enriched.append(post)
            continue
        processed += 1
        print(f"[detail] {index}/{len(posts)} {post.post_id}", flush=True)

        result: SocialPost | None = None
        last_exc: Exception | None = None
        for attempt in range(1, args.retry + 2):
            try:
                result = enrich_one(page, post, config)
                break
            except Exception as exc:
                last_exc = exc
                print(f"[retry] {post.post_id} attempt={attempt} {type(exc).__name__}: {exc}", flush=True)
                try:
                    page = new_page()
                except Exception:
                    pass
                time.sleep(3)

        if result is None:
            failed += 1
            print(f"[failed] {post.post_id} {type(last_exc).__name__ if last_exc else 'Unknown'}", flush=True)
            enriched.append(post)
        else:
            enriched.append(result)
            print(
                f"[ok] title={result.title[:24]!r} content={len(result.content)} "
                f"images={len(result.image_urls)} videos={len(result.video_urls)}",
                flush=True,
            )

    write_jsonl(args.output, enriched)
    stats = build_stats(
        "xiaohongshu",
        enriched,
        visited_users=len({post.author_id for post in enriched if post.author_id}),
        failed=failed,
    )
    save_stats(stats, args.stats)
    print(f"[done] posts={len(enriched)} failed={failed} output={args.output}", flush=True)


if __name__ == "__main__":
    main()
