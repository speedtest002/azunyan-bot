import aiohttp
import logging
import urllib.parse

API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
log = logging.getLogger("azunyan.dictionary")

async def lookup_word(session: aiohttp.ClientSession, word: str) -> str | None:
    url = f"{API_URL}{urllib.parse.quote(word)}"
    async with session.get(url) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()

    meanings = []
    for meaning in data[0].get("meanings", []):
        pos = meaning.get("partOfSpeech", "")
        for definition in meaning.get("definitions", []):
            meanings.append(f"- ({pos}): {definition['definition']}")

    meanings_text = "\n".join(meanings)
    
    return meanings_text