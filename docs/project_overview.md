# AI 实训：数据爬取项目

## 课程材料

课件位于 `courseware/`：

| 文件 | 主题 |
|------|------|
| `01-m3u8流媒体数据获取.pptx` | m3u8 格式解析、ts 分片下载、ffmpeg 合并 |
| `02-图书数据爬取.pptx` | Scrapy 框架、Celery 分布式调度、Redis+MongoDB |
| `03-反爬虫技术应对.pptx` | HTTP 伪装、IP 代理、验证码识别、Selenium 指纹对抗 |
| `04-社交媒体数据获取.pptx` | 小红书综合采集：DrissionPage + Socket + 验证码 |

## 实验详情

### 实验1：m3u8 流媒体下载（`exp1_m3u8/`）

- **入口**：`m3u8_downloader.py`
- **输出**：`downloads/`（ts 分片 + 合并后的 mp4）
- **核心依赖**：requests, BeautifulSoup, re, ffmpeg, threading

### 实验2：分布式图书爬虫（`exp2_scrapy/`）

- **入口**：`scrapy.cfg` → `book_crawler/`
- **调度**：`celery_app.py` + `run_celery_task.py` + `seed_redis.py`
- **基础设施**：`docker-compose.yml`（Redis + MongoDB）
- **输出**：`outputs/books.jsonl`
- **核心依赖**：Scrapy, scrapy-redis, Celery, Redis, pymongo

### 实验3：反爬虫技术（`exp3_anti_crawl/`）

- **代码**：`anti_crawl_lab/client_demo.py` + `mock_site.py`
- **输出**：`outputs/anti_crawl_demo.json`
- **覆盖技术**：User-Agent 伪装、代理 IP、OCR 验证码识别、Selenium webdriver 隐藏

### 实验4：社交媒体数据获取（`exp4_social_media/`）

最终综合任务，详见 `social_media_crawler/README.md`。

```
exp4_social_media/
├── social_media_crawler/
│   ├── src/          # 核心代码（client/parser/storage 等 10 个模块）
│   ├── config/       # 配置文件（.example.json 为模板，.local.json 不入库）
│   ├── data/         # 采集输出（JSONL + 统计 JSON）
│   ├── logs/         # 运行日志
│   └── tests/        # 解析器单元测试
├── scripts/          # 种子发现、并行增强、爬取启动
├── delivery/         # 最终提交包（代码 + 报告 + 数据集）
├── reports/          # 实验报告 Markdown 源 + 图表 + Pandoc 构建脚本
└── test_explore_parser.py
```

## 运行约定

本项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 依赖和命令运行：

```powershell
uv sync                          # 安装全部依赖
uv run python <script.py>        # 运行脚本
uv run scrapy crawl <spider>     # 启动 Scrapy 爬虫
uv add <package>                 # 添加新依赖
```
