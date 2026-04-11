import aiohttp
import hikari

from plugins.dictionary.core import lookup_word

async def dictionary_embed(session: aiohttp.ClientSession, word: str) -> hikari.Embed:
    meanings: str | None = await lookup_word(session, word)
    embed = hikari.Embed(
        title=f"'{word}'"
    )
    embed.set_footer(
        text="Powered by dictionaryapi.dev",
        icon="https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://dictionaryapi.dev&size=128"
        )
    if not meanings:
        embed.description = "**Word not found or an error occurred.**"
        embed.color = 0xFF0000
    else:
        embed.description = meanings
        embed.color = 0x00FF00
    return embed
