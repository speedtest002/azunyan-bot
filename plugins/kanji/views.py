import aiohttp
import hikari

from plugins.kanji.core import kanji_parsed


async def kanji_embed(session: aiohttp.ClientSession, kanji: str) -> hikari.Embed | str:
    payload = await kanji_parsed(session, kanji)
    if isinstance(payload, str):
        return payload

    embed = hikari.Embed(
        title=payload["title"],
        description=payload.get("description") or hikari.UNDEFINED,
        color=payload["color"],
    )
    for field in payload["fields"]:
        embed.add_field(field["name"], field["value"], inline=field["inline"])
    return embed
