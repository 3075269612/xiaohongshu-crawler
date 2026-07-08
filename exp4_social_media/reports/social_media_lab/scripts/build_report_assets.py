from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
DATA_PATH = PROJECT / "social_media_crawler" / "data" / "xhs_posts.jsonl"
ENRICHED_PATH = PROJECT / "social_media_crawler" / "data" / "xhs_posts_enriched.jsonl"
OUT_DATA = ROOT / "data"
OUT_FIGS = ROOT / "figs"


def read_rows() -> list[dict]:
    return [json.loads(line) for line in DATA_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_svg_bar(path: Path, title: str, labels: list[str], values: list[int]) -> None:
    width, height = 920, 420
    margin_left, margin_right, margin_top, margin_bottom = 170, 40, 70, 60
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    max_v = max(values) if values else 1
    bar_h = min(58, plot_h / max(1, len(values)) * 0.62)
    gap = (plot_h - bar_h * len(values)) / max(1, len(values) - 1) if len(values) > 1 else 0
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="36" text-anchor="middle" font-size="22" fill="black" font-family="Microsoft YaHei, SimSun, sans-serif">{title}</text>',
        f'<line x1="{margin_left}" y1="{height-margin_bottom}" x2="{width-margin_right}" y2="{height-margin_bottom}" stroke="black"/>',
    ]
    for index, (label, value) in enumerate(zip(labels, values)):
        y = margin_top + index * (bar_h + gap)
        bar_w = plot_w * value / max_v
        parts.append(f'<text x="{margin_left-12}" y="{y + bar_h*0.68:.1f}" text-anchor="end" font-size="16" fill="black" font-family="Microsoft YaHei, SimSun, sans-serif">{label}</text>')
        parts.append(f'<rect x="{margin_left}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="white" stroke="black"/>')
        parts.append(f'<text x="{margin_left + bar_w + 8:.1f}" y="{y + bar_h*0.68:.1f}" font-size="16" fill="black" font-family="Arial, sans-serif">{value}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def write_svg_composition(path: Path, normal: int, video: int) -> None:
    width, height = 760, 360
    total = max(1, normal + video)
    normal_w = int(520 * normal / total)
    video_w = 520 - normal_w
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="380" y="42" text-anchor="middle" font-size="22" fill="black" font-family="Microsoft YaHei, SimSun, sans-serif">帖子类型构成</text>',
        '<rect x="120" y="120" width="520" height="70" fill="white" stroke="black"/>',
        f'<rect x="120" y="120" width="{video_w}" height="70" fill="black"/>',
        f'<rect x="{120 + video_w}" y="120" width="{normal_w}" height="70" fill="white" stroke="black"/>',
        f'<text x="120" y="225" font-size="18" fill="black" font-family="Microsoft YaHei, SimSun, sans-serif">视频帖：{video} 条</text>',
        f'<text x="120" y="260" font-size="18" fill="black" font-family="Microsoft YaHei, SimSun, sans-serif">普通图文帖：{normal} 条</text>',
        f'<text x="120" y="295" font-size="18" fill="black" font-family="Microsoft YaHei, SimSun, sans-serif">总计：{total} 条</text>',
        '</svg>',
    ]
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    rows = read_rows()

    # Load enriched sample for content stats
    enriched = []
    if ENRICHED_PATH.exists():
        enriched = [json.loads(line) for line in ENRICHED_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]

    by_author: dict[str, dict] = {}
    for row in rows:
        author_id = row.get("author_id", "")
        name = row.get("author_name", "") or author_id
        entry = by_author.setdefault(author_id, {"author_id": author_id, "author_name": name, "posts": 0, "videos": 0})
        entry["posts"] += 1
        if row.get("has_video"):
            entry["videos"] += 1

    authors = sorted(by_author.values(), key=lambda item: item["posts"], reverse=True)
    # Top 10 for chart, full list for CSV
    top_authors = authors[:10]

    summary = {
        "platform": "xiaohongshu",
        "posts": len(rows),
        "unique_authors": len(by_author),
        "video_posts": sum(1 for row in rows if row.get("has_video")),
        "normal_posts": sum(1 for row in rows if not row.get("has_video")),
        "content_nonempty": sum(1 for row in enriched if row.get("content")),
        "image_url_count": sum(len(row.get("image_urls") or []) for row in enriched),
        "video_url_count": sum(len(row.get("video_urls") or []) for row in enriched),
        "enriched_sample": len(enriched),
        "authors": authors,
    }
    (OUT_DATA / "xhs_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT_DATA / "author_summary.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["author_id", "author_name", "posts", "videos"])
        writer.writeheader()
        writer.writerows(authors)

    write_svg_bar(
        OUT_FIGS / "fig-author-posts.svg",
        "各作者采集帖子数（Top 10）",
        [item["author_name"] for item in top_authors],
        [item["posts"] for item in top_authors],
    )
    video = summary["video_posts"]
    normal = summary["normal_posts"]
    write_svg_composition(OUT_FIGS / "fig-data-composition.svg", normal, video)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
