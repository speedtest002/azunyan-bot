from __future__ import annotations

from dataclasses import dataclass

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from core.config import Settings


@dataclass(slots=True)
class MongoResources:
    client: AsyncMongoClient
    database: AsyncDatabase

    def collection(self, name: str) -> AsyncCollection:
        if not name:
            raise ValueError("Collection name is required.")

        return self.database[name]


def create_mongo_resources(settings: Settings) -> MongoResources:
    client = AsyncMongoClient(settings.mongo_uri or None)
    database = client[settings.mongo_db_name]
    return MongoResources(client=client, database=database)
