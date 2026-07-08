from urllib.parse import urljoin

import scrapy
from scrapy_redis.spiders import RedisSpider

from book_crawler.items import BookItem


RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


def extract_books(response):
    category = response.css(".page-header.action h1::text").get(default="Books").strip()

    for book in response.css("article.product_pod"):
        detail_url = response.urljoin(book.css("h3 a::attr(href)").get())
        rating_class = book.css("p.star-rating::attr(class)").get(default="")
        rating_word = rating_class.replace("star-rating", "").strip()

        yield BookItem(
            title=book.css("h3 a::attr(title)").get(default="").strip(),
            price=book.css(".price_color::text").get(default="").strip(),
            rating=RATING_MAP.get(rating_word),
            availability=" ".join(book.css(".availability::text").getall()).strip(),
            detail_url=detail_url,
            category=category,
        )


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    def parse(self, response):
        yield from extract_books(response)

        next_href = response.css("li.next a::attr(href)").get()
        if next_href:
            yield response.follow(next_href, callback=self.parse)


class BooksRedisSpider(RedisSpider):
    name = "books_redis"
    allowed_domains = ["books.toscrape.com"]
    redis_key = "books:start_urls"
    custom_settings = {
        "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
        "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
        "SCHEDULER_PERSIST": True,
    }

    def parse(self, response):
        yield from extract_books(response)

        next_href = response.css("li.next a::attr(href)").get()
        if next_href:
            yield response.follow(next_href, callback=self.parse)


def absolute_book_url(path):
    return urljoin("https://books.toscrape.com/", path)