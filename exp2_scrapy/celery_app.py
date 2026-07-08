import os
import subprocess

from celery import Celery


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery("data_crawler_tasks", broker=REDIS_URL, backend=REDIS_URL)


@app.task(name="crawl_books")
def crawl_books(item_limit=100):
    command = [
        "uv",
        "run",
        "scrapy",
        "crawl",
        "books",
        "-s",
        f"CLOSESPIDER_ITEMCOUNT={int(item_limit)}",
    ]
    completed = subprocess.run(command, text=True, capture_output=True)
    return {
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }
