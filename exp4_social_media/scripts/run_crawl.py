"""Run the XHS user profile crawler in a loop until targets are reached."""
import subprocess, sys
from pathlib import Path

CONFIG = "social_media_crawler/config/xiaohongshu.final.local.json"
SEED_SCRIPT = "scripts/discover_seeds.py"

for round_num in range(1, 20):
    print(f"\n{'='*60}")
    print(f"ROUND {round_num}")
    print(f"{'='*60}")

    # Run crawler
    result = subprocess.run(
        [sys.executable, "-m", "social_media_crawler.src.xhs_manual_client",
         "--browser", "--config", CONFIG],
        cwd=".",
        env={**__import__('os').environ, "PYTHONPATH": "."}
    )

    if result.returncode != 0:
        print(f"Crawler exited with code {result.returncode}, stopping")
        break

    # Check if queue is empty
    qpath = Path("social_media_crawler/data/xhs_user_queue.txt")
    qurls = [l for l in qpath.read_text(encoding='utf-8').splitlines()
             if l.strip() and not l.startswith('#')] if qpath.exists() else []

    if qurls:
        print(f"Queue still has {len(qurls)} URLs, continuing")
        continue

    # Queue empty, discover more seeds
    print("Queue empty, discovering new seeds...")
    result = subprocess.run(
        [sys.executable, SEED_SCRIPT],
        cwd=".",
        env={**__import__('os').environ, "PYTHONPATH": "."}
    )

    # Check if we discovered anything new
    qurls = [l for l in qpath.read_text(encoding='utf-8').splitlines()
             if l.strip() and not l.startswith('#')] if qpath.exists() else []
    if not qurls:
        print("No more seeds to discover, stopping")
        break

print("Pipeline completed")
