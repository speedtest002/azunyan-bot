from __future__ import annotations

from dataclasses import dataclass

from pymongo.asynchronous.collection import AsyncCollection


@dataclass(slots=True)
class NoteRepository:
    collection: AsyncCollection

    async def exists(self, key: str) -> bool:
        return await self.collection.find_one({"key": key}, {"_id": 1}) is not None

    async def create(self, key: str, text: str) -> None:
        await self.collection.insert_one({"key": key, "text": text})

    async def get_text(self, key: str) -> str | None:
        document = await self.collection.find_one({"key": key})
        if document is None:
            return None

        text = document.get("text")
        return str(text) if text is not None else None
