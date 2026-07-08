import argparse
import concurrent.futures
import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin

import requests


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

M3U8_PATTERN = re.compile(r"https?://[^\s\"']+?\.m3u8(?:\?[^\s\"']*)?")


def fetch_text(url, headers=None, timeout=20):
    response = requests.get(url, headers=headers or DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def extract_m3u8_urls(page_url, html):
    urls = set(M3U8_PATTERN.findall(html))

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        BeautifulSoup = None

    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["a", "source", "video", "script"]):
            for attr in ("src", "href"):
                value = tag.get(attr)
                if value and ".m3u8" in value:
                    urls.add(urljoin(page_url, value))

    return sorted(urls)


def resolve_input_to_m3u8(input_url):
    if ".m3u8" in input_url:
        return input_url

    html = fetch_text(input_url)
    candidates = extract_m3u8_urls(input_url, html)
    if not candidates:
        raise RuntimeError(
            "没有在网页源码中找到 m3u8 链接。请在浏览器 F12 -> Network 中过滤 m3u8，"
            "复制真实 m3u8 URL 后再运行。"
        )
    return candidates[0]


def parse_m3u8(m3u8_url, m3u8_text):
    ts_urls = []
    nested_m3u8_urls = []

    for raw_line in m3u8_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        absolute_url = urljoin(m3u8_url, line)
        if ".m3u8" in line:
            nested_m3u8_urls.append(absolute_url)
        else:
            ts_urls.append(absolute_url)

    return nested_m3u8_urls, ts_urls


def load_media_playlist(m3u8_url):
    text = fetch_text(m3u8_url)
    nested_m3u8_urls, ts_urls = parse_m3u8(m3u8_url, text)

    if ts_urls:
        return m3u8_url, text, ts_urls
    if nested_m3u8_urls:
        selected_url = nested_m3u8_urls[-1]
        selected_text = fetch_text(selected_url)
        _, selected_ts_urls = parse_m3u8(selected_url, selected_text)
        return selected_url, selected_text, selected_ts_urls

    raise RuntimeError("m3u8 文件中没有找到 ts 片段，也没有找到二级 m3u8。")


def download_one(index, url, output_dir):
    filename = f"{index:05d}.ts"
    output_path = output_dir / filename
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path

    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path


def download_ts_files(ts_urls, output_dir, workers=8):
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(download_one, index, url, output_dir)
            for index, url in enumerate(ts_urls)
        ]
        for done, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            path = future.result()
            results.append(path)
            print(f"[{done}/{len(ts_urls)}] downloaded {path.name}")
    return sorted(results)


def write_concat_list(ts_files, concat_file):
    concat_file.write_text(
        "\n".join(f"file '{path.as_posix()}'" for path in ts_files) + "\n",
        encoding="utf-8",
    )


def merge_with_ffmpeg(concat_file, output_mp4):
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(output_mp4),
    ]
    subprocess.run(command, check=True)


def merge_by_binary_concat(ts_files, output_ts):
    with output_ts.open("wb") as out:
        for path in ts_files:
            out.write(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description="m3u8 流媒体下载实验脚本")
    parser.add_argument("url", help="网页 URL 或 m3u8 URL")
    parser.add_argument("-o", "--output", default="downloads/video", help="输出目录")
    parser.add_argument("-w", "--workers", type=int, default=8, help="下载线程数")
    parser.add_argument("--dry-run", action="store_true", help="只解析，不下载")
    args = parser.parse_args()

    output_dir = Path(args.output)
    segments_dir = output_dir / "segments"
    output_dir.mkdir(parents=True, exist_ok=True)

    m3u8_url = resolve_input_to_m3u8(args.url)
    media_m3u8_url, m3u8_text, ts_urls = load_media_playlist(m3u8_url)

    (output_dir / "index.m3u8").write_text(m3u8_text, encoding="utf-8")
    (output_dir / "ts_urls.txt").write_text("\n".join(ts_urls) + "\n", encoding="utf-8")

    print(f"m3u8: {media_m3u8_url}")
    print(f"ts count: {len(ts_urls)}")

    if args.dry_run:
        print(f"已保存 m3u8 和 ts 列表到 {output_dir}")
        return

    ts_files = download_ts_files(ts_urls, segments_dir, args.workers)
    concat_file = output_dir / "concat.txt"
    write_concat_list(ts_files, concat_file)

    output_mp4 = output_dir / "video.mp4"
    try:
        merge_with_ffmpeg(concat_file, output_mp4)
        print(f"完成：{output_mp4}")
    except (FileNotFoundError, subprocess.CalledProcessError):
        output_ts = output_dir / "video.ts"
        merge_by_binary_concat(ts_files, output_ts)
        print("没有检测到可用的 ffmpeg，已先按二进制方式合并为 TS 文件：")
        print(output_ts)
        print("安装 ffmpeg 后可用 concat.txt 转成 mp4。")


if __name__ == "__main__":
    main()
