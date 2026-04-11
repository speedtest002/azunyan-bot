from __future__ import annotations

import aiohttp


async def create_http_session() -> aiohttp.ClientSession:
    timeout = aiohttp.ClientTimeout(total=20)
    return aiohttp.ClientSession(timeout=timeout)
