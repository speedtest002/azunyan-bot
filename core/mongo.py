from pymongo import MongoClient
from core.config import MONGO_URI


class MongoManager:
    _client: MongoClient | None = None

    @staticmethod
    def get_client() -> MongoClient:
        if MongoManager._client is None:
            MongoManager._client = MongoClient(MONGO_URI)
        return MongoManager._client

    @staticmethod
    def get_database(db_name: str):
        if not db_name:
            raise ValueError("db_name is required")
        return MongoManager.get_client()[db_name]

    @staticmethod
    def get_collection(collection_name: str, db_name: str = "azunyan"):
        if not db_name:
            raise ValueError("db_name is required")
        if not collection_name:
            raise ValueError("collection_name is required")
        return MongoManager.get_database(db_name)[collection_name]
