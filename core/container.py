from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import aiohttp

from core.config import Settings
from core.db import MongoResources


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    mongo: MongoResources
    http: aiohttp.ClientSession
    _services: dict[type[Any], Any] = field(default_factory=dict)

    @property
    def database(self):
        return self.mongo.database

    def has(self, typ: type[Any]) -> bool:
        return typ in self._services

    def register(self, typ: type[Any], value: Any) -> Any:
        self._services[typ] = value
        return value

    def resolve(self, typ: type[Any]) -> Any:
        return self._services[typ]

    async def aclose(self) -> None:
        if not self.http.closed:
            await self.http.close()

        await self.mongo.client.close()
