"""plugins/partyrank/client.py — HTTP client cho Party Rank backend"""
import logging

import aiohttp

from core.config import API_BASE_URL, BOT_SECRET

logger = logging.getLogger("azunyan.partyrank")


async def call_api(session: aiohttp.ClientSession, endpoint: str, payload: dict) -> tuple[dict, int]:
    base = API_BASE_URL.rstrip("/")
    url = f"https://{base}/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {BOT_SECRET}", "Content-Type": "application/json"}
    try:
        async with session.post(url, json=payload, headers=headers) as resp:
            return await resp.json(), resp.status
    except Exception as e:
        logger.error("API call error to %s: %s", endpoint, e, exc_info=True)
        return {"error": "Internal connection error"}, 500
