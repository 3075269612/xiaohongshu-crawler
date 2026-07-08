import json
import os
from pathlib import Path

from itemadapter import ItemAdapter
from pymongo import MongoClient


class JsonLinesPipeline:
    def open_spider(self, spider):
        output_dir = Path(os.getenv("BOOK_OUTPUT_DIR", "outputs"))
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_path = output_dir / f"{spider.name}.jsonl"
        self.file = self.output_path.open("w", encoding="utf-8")

    def close_spider(self, spider):
        self.file.close()
        spider.logger.info("JSONL output saved to %s", self.output_path)

    def process_item(self, item, spider):
        record = dict(ItemAdapter(item))
        self.file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return item


class MongoPipeline:
    def open_spider(self, spider):
        self.client = None
        self.collection = None
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        database = os.getenv("MONGO_DATABASE", "data_crawler")
        collection = os.getenv("MONGO_COLLECTION", "books")

        try:
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            self.client.admin.command("ping")
            self.collection = self.client[database][collection]
            self.collection.create_index("detail_url", unique=True)
            spider.logger.info("MongoDB connected: %s/%s", database, collection)
        except Exception as exc:
            spider.logger.warning("MongoDB unavailable, JSONL output still works: %s", exc)
            if self.client:
                self.client.close()
            self.client = None

    def close_spider(self, spider):
        if self.client:
            self.client.close()

    def process_item(self, item, spider):
        if self.collection is None:
            return item

        record = dict(ItemAdapter(item))
        self.collection.update_one(
            {"detail_url": record.get("detail_url")},
            {"$set": record},
            upsert=True,
        )
        return item
