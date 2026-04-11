from __future__ import annotations

from dataclasses import dataclass

from plugins.note.repository import NoteRepository


class NoteError(Exception):
    """Base exception for note domain errors."""


class NoteAlreadyExistsError(NoteError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Note with key {key!r} already exists.")
        self.key = key


class NoteNotFoundError(NoteError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Note with key {key!r} was not found.")
        self.key = key


@dataclass(slots=True)
class NoteService:
    repository: NoteRepository

    async def save(self, key: str, text: str) -> None:
        normalized_key = key.strip()
        if await self.repository.exists(normalized_key):
            raise NoteAlreadyExistsError(normalized_key)

        await self.repository.create(normalized_key, text)

    async def get(self, key: str) -> str:
        normalized_key = key.strip()
        text = await self.repository.get_text(normalized_key)
        if text is None:
            raise NoteNotFoundError(normalized_key)

        return text
