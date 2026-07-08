import argparse
import json

from celery_app import crawl_books


def main():
    parser = argparse.ArgumentParser(description="Submit a Celery task that runs the Scrapy books spider")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    result = crawl_books.delay(args.limit)
    print(f"task id: {result.id}")
    payload = result.get(timeout=args.timeout)
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()