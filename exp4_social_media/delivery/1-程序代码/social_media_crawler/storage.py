from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pymongo import MongoClient

from .models import SocialPost


class JsonlStorage:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_many(self, posts: Iterable[SocialPost]) -> int:
        count = 0
        with self.path.open("a", encoding="utf-8") as file:
            for post in posts:
                file.write(json.dumps(post.to_dict(), ensure_ascii=False) + "\n")
                count += 1
        return count


class MongoStorage:
    def __init__(self, uri: str, database: str, collection: str):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        self.collection = self.client[database][collection]
        self.collection.create_index("url", unique=True)

    def write_many(self, posts: Iterable[SocialPost]) -> int:
        count = 0
        for post in posts:
            self.collection.update_one(
                {"url": post.url},
                {"$set": post.to_dict()},
                upsert=True,
            )
            count += 1
        return count

    def close(self) -> None:
        self.client.close()