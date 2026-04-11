import aiohttp
import os
import logging
from plugins.song.views import SongPaginationView

log = logging.getLogger("azunyan.song")

ANISONGDB_URL = os.getenv("ANISONGDB_URL", "")
MEDIA_URL = os.getenv("MEDIA_URL", "")

async def search_songs(session: aiohttp.ClientSession, query: str) -> list:
    url = f"{ANISONGDB_URL}/api/song/search"
    try:
        async with session.get(url, params={"name": query}) as resp:
            return await resp.json() if resp.status == 200 else []
    except Exception as e:
        log.error("AnisongDB error: %s", e)
        return []

def format_result(song: dict) -> dict:
    anime_name = song.get("animeNameJa") or song.get("animeNameEn") or "N/A"
    mal_id = song.get("malId")
    anime_display = f"[{anime_name}](https://myanimelist.net/anime/{mal_id})" if mal_id else anime_name

    song_name = song.get("songName") or "N/A"
    video = song.get("hq") or song.get("mq")
    song_display = f"[{song_name}]({MEDIA_URL}/{video})" if video and MEDIA_URL else song_name

    artist = song.get("songArtist") or "N/A"
    audio = song.get("audio")
    artist_display = f"[{artist}]({MEDIA_URL}/{audio})" if audio and MEDIA_URL else artist

    return {"anime": anime_display, "song": song_display, "artist": artist_display}

async def build_search_view(session: aiohttp.ClientSession, query: str, dedup: bool, author_id: int):
    results = await search_songs(session, query)
    if not results:
        return "Không tìm thấy kết quả nào.", None

    if dedup:
        seen: set[str] = set()
        deduped = []
        for r in results:
            key = r.get("songName", "")
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        results = deduped

    results.sort(key=lambda x: len(x.get("songName", "")))

    view = SongPaginationView(results, format_result, author_id)
    embed = view.create_embed()
    return embed, view