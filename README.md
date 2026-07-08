# 小红书社交媒体数据采集

基于 DrissionPage 的小红书（xiaohongshu.com）自动化数据采集项目，支持用户主页解析、笔记详情增强、验证码自动绕过、多客户端并行采集，最终产出结构化 JSONL 数据集与统计分析报告。

## 核心能力

- **双阶段采集策略**：先通过用户主页 SSR 卡片批量获取笔记基础信息与 `xsec_token`，再低频访问详情页补全正文和媒体 URL，有效规避 404 拦截
- **验证码自动绕过**：滑块验证码角度预测 API + 人类轨迹模拟（随机速度曲线、微调抖动、终点犹豫）
- **多客户端架构**：Socket 通信从服务端拉取种子 URL，支持多机并行采集
- **双写存储**：JSONL 文件 + MongoDB，兼顾可读性与查询便利
- **邮件告警**：验证码失败、请求异常时 SMTP 实时通知
- **统计面板**：请求成功率、采集速度、数据分布一目了然

## 快速开始

```powershell
# 安装依赖
uv sync

# 启动 MongoDB（可选，仅双写模式需要）
docker compose -f exp2_scrapy/docker-compose.yml up -d

# 运行采集（手动登录模式）
uv run python exp4_social_media/social_media_crawler/src/xhs_manual_client.py

# 或 Feed 流采集模式
uv run python exp4_social_media/social_media_crawler/src/xhs_feed_client.py

# 详情增强
uv run python exp4_social_media/scripts/parallel_enrich.py
```

## 项目结构

```
├── exp4_social_media/              ★ 核心项目
│   ├── social_media_crawler/
│   │   ├── src/                    # 10 个核心模块（详见子目录 README）
│   │   ├── config/                 # 配置文件（.example 模板，.local 不入库）
│   │   ├── data/                   # 采集数据与统计
│   │   └── tests/                  # 解析器单元测试
│   ├── scripts/                    # 辅助脚本（种子发现、并行增强、ffmpeg 合并）
│   ├── delivery/                   # 提交包（代码 + 实验报告 + 数据集）
│   └── reports/                    # 实验报告 Markdown 源 + 图表
├── exp1_m3u8/                      # 前置实验：m3u8 流媒体下载
├── exp2_scrapy/                    # 前置实验：Scrapy 分布式爬虫
├── exp3_anti_crawl/                # 前置实验：反爬虫技术应对
├── courseware/                     # 课程课件（4 个 PPT）
├── docs/                           # 各实验操作说明
├── pyproject.toml
└── uv.lock
```

## 前置基础实验

三个入门实验为本项目提供了关键技术积累：

| # | 主题 | 为本项目提供的技术储备 | 目录 |
|---|------|----------------------|------|
| 1 | m3u8 流媒体下载 | HTTP 请求伪装、多线程下载、ffmpeg 合并 | `exp1_m3u8/` |
| 2 | Scrapy 分布式爬虫 | Redis 任务队列、MongoDB 存储、Celery 调度 | `exp2_scrapy/` |
| 3 | 反爬虫对抗 | User-Agent 伪装、代理 IP、OCR 验证码、Selenium 指纹隐藏 | `exp3_anti_crawl/` |

> **分布式扩展方向**：当前实验4 为单机 Socket 多客户端架构。生产环境中可引入实验2 的 **Celery + Redis + Scrapy** 方案，将用户主页采集、详情增强、验证码处理拆分为独立 Task，由多 Worker 节点并行消费 Redis 队列，实现横向扩展与任务去重。

## 环境要求

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) 包管理器
- MongoDB（可选，双写存储需要）
- ffmpeg（可选，视频下载需要）
