# Social Media Crawler

实验4 综合任务——社交媒体数据获取，目标平台为小红书（xiaohongshu.com）。

## 架构

```
client (DrissionPage + Socket)  ←→  server (任务分发)
       │
       ├── captcha_solver  →  验证码角度预测 + 滑块轨迹模拟
       ├── xhs_parser      →  页面解析（用户主页 / 笔记详情 / 搜索流）
       ├── xhs_feed_client →  推荐流采集
       ├── xhs_manual_client → 手动登录 + Cookie 维护
       ├── storage         →  JSONL + MongoDB 双写
       ├── statistics      →  采集统计与成功率计算
       ├── task_queue      →  用户队列管理
       └── zemail          →  邮件异常通知
```

## 模块说明

| 模块 | 职责 |
|------|------|
| `client.py` | Socket 通信，连接服务端获取种子 URL |
| `captcha_solver.py` | 滑块验证码识别（角度预测 API + 人类轨迹模拟） |
| `xhs_parser.py` | 从页面 SSR 数据解析笔记卡片、作者信息、xsecToken |
| `xhs_feed_client.py` | Feed 流采集与滚动加载 |
| `xhs_manual_client.py` | 手动登录会话管理 |
| `xhs_detail_enricher.py` | 基于带 token 的详情 URL 补全正文和媒体字段 |
| `models.py` | Post / Author 数据模型 |
| `storage.py` | JSONL 文件 + MongoDB 双写存储 |
| `statistics.py` | 请求成功率、采集速度等统计 |
| `task_queue.py` | Redis 任务队列管理 |
| `zemail.py` | SMTP 邮件告警 |

## 运行

```powershell
# 手动登录模式
uv run python -m social_media_crawler.src.xhs_manual_client

# Feed 采集模式
uv run python -m social_media_crawler.src.xhs_feed_client

# 详情增强（需要先采集基础卡片数据）
uv run python scripts/parallel_enrich.py
```
