# 第一次实验：m3u8 流媒体格式数据获取

## 四个 PPT 的整体关系

1. `数据爬取1.pptx`：m3u8 视频流下载实验，核心是找到 m3u8、解析 ts、下载分片、合并视频。
2. `数据爬取2.pptx`：Scrapy、Celery、Redis、MongoDB，偏分布式图文爬虫。
3. `数据爬取3.pptx`：请求头、代理、验证码、Selenium 指纹等反爬技术。
4. `数据爬取4.pptx`：社交媒体综合爬取任务，最终要提交代码、数据和实验报告。

当前先完成第 1 个 PPT。

## 第 1 步：找到 m3u8 URL

PPT 推荐从浏览器手动分析开始：

1. 打开一个视频网页，例如 PPT 里的 AcFun 示例。
2. 按 `F12` 打开开发者工具。
3. 切换到 `Network`。
4. 刷新页面并播放视频。
5. 在过滤框输入 `m3u8`。
6. 复制真实的 `.m3u8` 请求 URL。

如果网页源码里直接暴露了 m3u8，本项目脚本也可以自动提取；如果没有暴露，就按上面的 F12 方法复制。

## 运行方式

只解析，不下载：

```powershell
python .\m3u8_downloader.py "你的m3u8或网页URL" --dry-run
```

完整下载并合并：

```powershell
python .\m3u8_downloader.py "你的m3u8或网页URL" -o downloads\demo
```

运行后会得到：

- `downloads/demo/index.m3u8`：下载到的 m3u8 文件。
- `downloads/demo/ts_urls.txt`：解析出的 ts 片段 URL。
- `downloads/demo/segments/`：下载到的 ts 文件。
- `downloads/demo/concat.txt`：给 ffmpeg 使用的合并清单。
- `downloads/demo/video.mp4`：安装 ffmpeg 时生成。
- `downloads/demo/video.ts`：没有 ffmpeg 时的备用合并结果。

## 当前环境提醒

本机已检测到 Python 和 `requests` 可用，但没有检测到 `ffmpeg`，也没有安装 `beautifulsoup4`。

这不影响第一步和 ts 下载；只是最终转成 mp4 时，建议安装 ffmpeg 后再运行一次。
