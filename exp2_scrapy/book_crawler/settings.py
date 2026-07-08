BOT_NAME = "book_crawler"

SPIDER_MODULES = ["book_crawler.spiders"]
NEWSPIDER_MODULE = "book_crawler.spiders"

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 0.25
COOKIES_ENABLED = False

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
}

ITEM_PIPELINES = {
    "book_crawler.pipelines.JsonLinesPipeline": 200,
    "book_crawler.pipelines.MongoPipeline": 300,
}

REDIS_URL = "redis://localhost:6379/0"
LOG_LEVEL = "INFO"
