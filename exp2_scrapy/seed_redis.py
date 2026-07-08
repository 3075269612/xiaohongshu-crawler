import json
import os

import redis


def main():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    key = os.getenv("BOOK_REDIS_KEY", "books:start_urls")
    start_url = os.getenv("BOOK_START_URL", "https://books.toscrape.com/")

    client = redis.from_url(redis_url)
    client.delete(key, "books_redis:requests", "books_redis:dupefilter")
    client.lpush(key, json.dumps({"url": start_url}))
    print(f"seeded {key}: {start_url}")


if __name__ == "__main__":
    main()