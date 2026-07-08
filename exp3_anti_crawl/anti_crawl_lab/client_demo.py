from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8008"
OUTPUT = Path("outputs/anti_crawl_demo.json")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Referer": f"{BASE_URL}/",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def short_response(response: requests.Response) -> dict:
    try:
        body = response.json()
    except ValueError:
        body = response.text[:120]
    return {"status": response.status_code, "body": body}


def naive_request() -> dict:
    response = requests.get(f"{BASE_URL}/api/data", timeout=10)
    return short_response(response)


def browser_like_request() -> dict:
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(f"{BASE_URL}/", timeout=10)
    response = session.get(f"{BASE_URL}/api/data", timeout=10)
    return short_response(response)


def rate_limit_demo() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(f"{BASE_URL}/", timeout=10)

    results = []
    for index in range(5):
        response = session.get(f"{BASE_URL}/api/data", timeout=10)
        results.append({"round": index + 1, **short_response(response)})
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "5"))
            time.sleep(retry_after)
    return results


def proxy_pool_concept_demo() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(f"{BASE_URL}/", timeout=10)

    fake_client_keys = ["proxy-a", "proxy-b", "proxy-c", "proxy-d", "proxy-e"]
    results = []
    for key in fake_client_keys:
        response = session.get(f"{BASE_URL}/api/data", headers={"X-Lab-Client-IP": key}, timeout=10)
        results.append({"client_key": key, **short_response(response)})
    return results


def captcha_demo() -> dict:
    session = requests.Session()
    session.headers.update(HEADERS)
    page = session.get(f"{BASE_URL}/captcha", timeout=10)
    match = re.search(r"请输入\s+(\d+)\s+\+\s+(\d+)\s+的结果", page.text)
    if not match:
        return {"status": "question_not_found"}
    answer = int(match.group(1)) + int(match.group(2))
    response = session.get(f"{BASE_URL}/captcha/verify", params={"answer": answer}, timeout=10)
    return {"question": match.group(0), "answer": answer, **short_response(response)}


def main():
    results = {
        "naive_request": naive_request(),
        "browser_like_request": browser_like_request(),
        "rate_limit_demo": rate_limit_demo(),
        "proxy_pool_concept_demo": proxy_pool_concept_demo(),
        "captcha_demo": captcha_demo(),
        "selenium_fingerprint_page": f"{BASE_URL}/fingerprint",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"saved: {OUTPUT}")


if __name__ == "__main__":
    main()