import aiohttp

from plugins.kanji.parser import parse_kanji

MAZII_URL = "https://mazii.net/api/search/kanji"

async def fetch_kanji(session: aiohttp.ClientSession, kanji: str) -> dict | str:
    payload = {"dict": "javi", "type": "kanji", "query": kanji, "page": 1}
    async with session.post(MAZII_URL, json=payload) as resp:
        resp.raise_for_status()
        return await resp.json()

async def kanji_parsed(session: aiohttp.ClientSession, kanji: str) -> dict | str:
    kanji_json = await fetch_kanji(session, kanji)
    if isinstance(kanji_json, str):
        return kanji_json
    return parse_kanji(kanji_json)
