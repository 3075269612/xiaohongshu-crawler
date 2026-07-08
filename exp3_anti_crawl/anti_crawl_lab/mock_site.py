from __future__ import annotations

import json
import random
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
PORT = 8008
WINDOW_SECONDS = 5
MAX_REQUESTS_PER_WINDOW = 3

rate_windows: dict[str, list[float]] = {}
captcha_answers: dict[str, int] = {}


def parse_cookie(header: str | None) -> dict[str, str]:
    if not header:
        return {}
    cookie = SimpleCookie()
    cookie.load(header)
    return {key: morsel.value for key, morsel in cookie.items()}


class AntiCrawlerDemoHandler(BaseHTTPRequestHandler):
    server_version = "AntiCrawlerDemo/0.1"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def write_text(self, status: int, text: str, content_type: str = "text/plain; charset=utf-8", headers=None):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def write_json(self, status: int, payload: dict, headers=None):
        self.write_text(status, json.dumps(payload, ensure_ascii=False, indent=2), "application/json; charset=utf-8", headers)

    def client_key(self) -> str:
        return self.headers.get("X-Lab-Client-IP") or self.client_address[0]

    def has_browser_headers(self) -> bool:
        user_agent = self.headers.get("User-Agent", "")
        referer = self.headers.get("Referer", "")
        cookies = parse_cookie(self.headers.get("Cookie"))
        return "Mozilla" in user_agent and referer.endswith("/") and cookies.get("lab_session") == "ok"

    def is_rate_limited(self) -> bool:
        key = self.client_key()
        now = time.time()
        window = [t for t in rate_windows.get(key, []) if now - t < WINDOW_SECONDS]
        rate_windows[key] = window
        if len(window) >= MAX_REQUESTS_PER_WINDOW:
            return True
        window.append(now)
        return False

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.handle_home()
        elif path == "/api/data":
            self.handle_data()
        elif path == "/captcha":
            self.handle_captcha()
        elif path == "/captcha/verify":
            self.handle_captcha_verify()
        elif path == "/fingerprint":
            self.handle_fingerprint()
        else:
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def handle_home(self):
        html = """
<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>反爬实验站</title></head>
<body>
  <h1>反爬实验站</h1>
  <ul>
    <li><a href="/api/data">需要浏览器请求头、Referer、Cookie 的 JSON 接口</a></li>
    <li><a href="/captcha">本地算术验证码</a></li>
    <li><a href="/fingerprint">Selenium 指纹演示页</a></li>
  </ul>
</body>
</html>
""".strip()
        self.write_text(
            HTTPStatus.OK,
            html,
            "text/html; charset=utf-8",
            {"Set-Cookie": "lab_session=ok; Path=/; SameSite=Lax"},
        )

    def handle_data(self):
        if not self.has_browser_headers():
            self.write_json(
                HTTPStatus.FORBIDDEN,
                {
                    "error": "blocked_by_header_rules",
                    "need": ["Mozilla User-Agent", "Referer ending with /", "lab_session cookie from /"],
                },
            )
            return

        if self.is_rate_limited():
            self.write_json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "too_many_requests", "retry_after_seconds": WINDOW_SECONDS},
                {"Retry-After": str(WINDOW_SECONDS)},
            )
            return

        self.write_json(
            HTTPStatus.OK,
            {
                "items": [
                    {"title": "A Light in the Attic", "rating": 3},
                    {"title": "Tipping the Velvet", "rating": 1},
                    {"title": "Soumission", "rating": 1},
                ],
                "client_key": self.client_key(),
                "message": "request accepted",
            },
        )

    def handle_captcha(self):
        a = random.randint(10, 30)
        b = random.randint(10, 30)
        challenge_id = str(random.randint(100000, 999999))
        captcha_answers[challenge_id] = a + b
        html = f"""
<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>本地验证码</title></head>
<body>
  <h1>本地算术验证码</h1>
  <p id="question">请输入 {a} + {b} 的结果</p>
  <p>提交地址：/captcha/verify?answer=你的答案</p>
</body>
</html>
""".strip()
        self.write_text(
            HTTPStatus.OK,
            html,
            "text/html; charset=utf-8",
            {"Set-Cookie": f"captcha_id={challenge_id}; Path=/; SameSite=Lax"},
        )

    def handle_captcha_verify(self):
        cookies = parse_cookie(self.headers.get("Cookie"))
        challenge_id = cookies.get("captcha_id")
        expected = captcha_answers.get(challenge_id)
        query = parse_qs(urlparse(self.path).query)
        answer = query.get("answer", [""])[0]
        if expected is not None and answer.isdigit() and int(answer) == expected:
            self.write_json(HTTPStatus.OK, {"captcha": "passed"})
        else:
            self.write_json(HTTPStatus.FORBIDDEN, {"captcha": "failed"})

    def handle_fingerprint(self):
        html = """
<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>Selenium 指纹演示</title></head>
<body>
  <h1>Selenium 指纹演示</h1>
  <pre id="result"></pre>
  <script>
    const result = {
      webdriver: navigator.webdriver,
      languages: navigator.languages,
      platform: navigator.platform,
      userAgent: navigator.userAgent,
    };
    document.getElementById('result').textContent = JSON.stringify(result, null, 2);
  </script>
</body>
</html>
""".strip()
        self.write_text(HTTPStatus.OK, html, "text/html; charset=utf-8")


def main():
    server = ThreadingHTTPServer((HOST, PORT), AntiCrawlerDemoHandler)
    print(f"Anti-crawler demo server: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()