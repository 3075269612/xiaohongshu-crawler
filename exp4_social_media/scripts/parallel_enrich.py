"""Parallel detail enrichment using multiple browser tabs."""
from __future__ import annotations

import argparse, json, random, sys, time, queue, threading
from pathlib import Path

from social_media_crawler.src.xhs_detail_enricher import (
    read_posts, merge_post, write_jsonl, is_blocked, is_unavailable_note
)
from social_media_crawler.src.xhs_parser import parse_note_html
from social_media_crawler.src.statistics import build_stats, save_stats


def enrich_worker(tab, post, config) -> dict | None:
    """Enrich a single post using a browser tab."""
    tab.get(post.url)
    time.sleep(random.uniform(
        float(config["request"].get("min_interval_seconds", 2)),
        float(config["request"].get("max_interval_seconds", 5)),
    ))
    if is_blocked(tab.html):
        return None  # signal captcha
    if is_unavailable_note(tab.url, tab.html):
        return post  # skip unavailable
    detail = parse_note_html(tab.html, post.url)
    return merge_post(post, detail)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="social_media_crawler/config/xiaohongshu.final.local.json")
    parser.add_argument("--input", default="social_media_crawler/data/xhs_posts.jsonl")
    parser.add_argument("--output", default="social_media_crawler/data/xhs_posts_enriched.jsonl")
    parser.add_argument("--stats", default="social_media_crawler/data/xhs_statistics_enriched.json")
    parser.add_argument("--tabs", type=int, default=3, help="Number of parallel browser tabs")
    parser.add_argument("--max", type=int, default=0)
    parser.add_argument("--skip-video", action="store_true", help="Skip video posts")
    parser.add_argument("--retry", type=int, default=2)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    from social_media_crawler.src.xhs_manual_client import load_config
    from DrissionPage import ChromiumOptions, ChromiumPage

    config = load_config(args.config)
    posts = read_posts(args.input)
    limit = args.max if args.max > 0 else len(posts)

    # Filter: skip already enriched and optionally video posts
    todo = []
    for p in posts:
        if p.raw.get("detail_enriched"):
            continue
        if args.skip_video and p.has_video:
            continue
        todo.append(p)
        if len(todo) >= limit:
            break

    print(f"Total posts: {len(posts)}, to enrich: {len(todo)}, tabs: {args.tabs}")

    # Create browser and tabs
    browser = ChromiumPage(ChromiumOptions())
    tabs = [browser]
    for _ in range(args.tabs - 1):
        tabs.append(browser.new_tab())

    # Results
    enriched_map: dict[str, object] = {}
    failed = 0
    processed = 0
    task_queue = queue.Queue()
    for p in todo:
        task_queue.put(p)

    # Also keep track of posts not in todo (already enriched or skipped)
    for p in posts:
        if p.post_id not in {t.post_id for t in todo}:
            enriched_map[p.post_id] = p

    lock = threading.Lock()

    def worker(tab, worker_id):
        nonlocal failed, processed
        while True:
            try:
                post = task_queue.get_nowait()
            except queue.Empty:
                break

            result = None
            for attempt in range(args.retry + 2):
                try:
                    result = enrich_worker(tab, post, config)
                    if result is None:  # captcha
                        print(f"[captcha] worker {worker_id} detected captcha on {post.post_id}")
                        break
                    break
                except Exception as exc:
                    print(f"[retry] {post.post_id} attempt={attempt} {type(exc).__name__}")
                    time.sleep(2)

            with lock:
                if result is not None:
                    enriched_map[post.post_id] = result
                    processed += 1
                else:
                    enriched_map[post.post_id] = post
                    failed += 1

            if processed % 50 == 0:
                print(f"[progress] {processed}/{len(todo)} enriched, {failed} failed")

            task_queue.task_done()

    # Run workers in threads (one per tab)
    threads = []
    for i, tab in enumerate(tabs):
        t = threading.Thread(target=worker, args=(tab, i + 1))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Close tabs
    for tab in tabs[1:]:
        try:
            tab.close()
        except Exception:
            pass
    try:
        tabs[0].quit()
    except Exception:
        pass

    # Write output (preserve original order)
    output_posts = [enriched_map.get(p.post_id, p) for p in posts]
    write_jsonl(args.output, [p for p in output_posts if isinstance(p, type(posts[0]))])

    stats = build_stats(
        "xiaohongshu",
        [p for p in output_posts if isinstance(p, type(posts[0]))],
        visited_users=len({p.author_id for p in output_posts if hasattr(p, 'author_id') and p.author_id}),
        failed=failed,
    )
    save_stats(stats, args.stats)

    enriched_count = sum(1 for p in output_posts if hasattr(p, 'raw') and p.raw.get("detail_enriched"))
    print(f"[done] posts={len(output_posts)} enriched={enriched_count} failed={failed}")


if __name__ == "__main__":
    main()
