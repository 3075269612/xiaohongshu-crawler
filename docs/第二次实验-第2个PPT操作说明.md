# 第二次实验：Scrapy 分布式图文数据获取

## 本项目对应 PPT 内容

- Scrapy 五大组件：Engine、Scheduler、Downloader、Spider、Item Pipeline。
- Redis：作为任务队列和去重调度基础。
- MongoDB：保存结构化爬取结果。
- Celery：把爬虫运行封装成可调度任务。
- Scrapy-Redis：展示从 Redis 队列读取起始 URL 的分布式爬虫入口。

本实验选择 `https://books.toscrape.com/` 作为公开练习站点，避免真实平台反爬和版权风险；代码结构仍对应 PPT 的分布式爬虫思想。

## 启动基础设施

```powershell
docker compose -p data-crawler up -d redis mongo
```

## 直接运行 Scrapy 爬虫

限制爬取 100 条，便于课堂演示：

```powershell
uv run scrapy crawl books -s CLOSESPIDER_ITEMCOUNT=100
```

输出位置：

- `outputs/books.jsonl`
- MongoDB：`mongodb://localhost:27017/data_crawler.books`

## Celery 调度演示

先启动 worker：

```powershell
uv run celery -A celery_app worker --loglevel=info --pool=solo --without-gossip --without-mingle --without-heartbeat -Q celery -c 1
```

另开一个终端投递任务：

```powershell
uv run python run_celery_task.py --limit 40
```

## Scrapy-Redis 队列演示

先把起始 URL 放入 Redis：

```powershell
uv run python seed_redis.py
```

再运行 Redis 版爬虫：

```powershell
uv run scrapy crawl books_redis -s CLOSESPIDER_ITEMCOUNT=40 -s CLOSESPIDER_TIMEOUT=60
```

## 与 PPT 的对应关系

1. 定义与配置：`pyproject.toml`、`scrapy.cfg`、`book_crawler/settings.py`
2. 爬虫实现：`book_crawler/spiders/books.py`
3. 数据存储：`book_crawler/pipelines.py`
4. 分布式任务调度：`celery_app.py`、`run_celery_task.py`
5. scrapy-redis 案例：`BooksRedisSpider`、`seed_redis.py`
