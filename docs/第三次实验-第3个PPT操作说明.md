# 第三次实验：反爬虫技术介绍及应对方法

## 本地实验目标

第 3 个 PPT 涉及真实网站常见反爬机制。为了让实验可复现、可截图，并避免绕过真实平台风控，本项目使用本地模拟站点完成演示：

- HTTP 请求头反爬：检查 `User-Agent`、`Referer`、`Cookie`。
- IP/频率限制：同一客户端短时间请求过多返回 `429`。
- 代理池思想：用本地 `X-Lab-Client-IP` 模拟不同出口 IP，不接入真实代理。
- 验证码：使用本地算术验证码演示“识别/提交/失败重试”流程，不破解真实验证码。
- Selenium 指纹：提供 `/fingerprint` 页面观察 `navigator.webdriver` 等字段。

## 启动本地反爬模拟站

```powershell
uv run python .\anti_crawl_lab\mock_site.py
```

服务地址：

```text
http://127.0.0.1:8008
```

## 运行客户端实验

另开一个终端：

```powershell
uv run python .\anti_crawl_lab\client_demo.py
```

输出文件：

```text
outputs\anti_crawl_demo.json
```

## 与 PPT 对应关系

1. HTTP 请求头反爬：`naive_request` 会失败，`browser_like_request` 通过请求头和 Cookie 成功。
2. IP 封禁/频率限制：`rate_limit_demo` 触发 `429` 并读取 `Retry-After` 等待。
3. 代理池管理：`proxy_pool_concept_demo` 用不同本地客户端标识模拟代理轮换思想。
4. 验证码反爬：`captcha_demo` 只处理本地算术验证码，用于学习流程，不用于真实验证码破解。
5. Selenium 指纹识别：浏览器打开 `/fingerprint` 可观察 `navigator.webdriver`、UA、语言等指纹字段。

## 报告可截图内容

- naive 请求被 403 拦截。
- 添加浏览器请求头、Referer、Cookie 后请求成功。
- 高频请求触发 429，等待后恢复。
- Redis/MongoDB 等第 2 个 PPT 服务可继续运行，但第 3 个 PPT 本地模拟站不依赖它们。