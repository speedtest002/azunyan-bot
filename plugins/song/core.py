import aiohttp
import logging
from core.config import ANISONGDB_URL, MEDIA_URL
from plugins.song.views import SongPaginationView

log = logging.getLogger("azunyan.song")

async def search_songs(session: aiohttp.ClientSession, query: str) -> list:
    url = f"{ANISONGDB_URL}/api/search_request"
    payload = {
        "and_logic": False,
        "ignore_duplicate": False,
        "opening_filter": True,
        "ending_filter": True,
        "insert_filter": True,
        "normal_broadcast": True,
        "dub": True,
        "rebroadcast": True,
        "standard": True,
        "character": True,
        "chanting": True,
        "instrumental": True,
        "tv_filter": True,
        "movie_filter": True,
        "ova_filter": True,
        "ona_filter": True,
        "special_filter": True,
        "doujin_filter": True,
        "anime_search_filter": {
            "search": query,
            "partial_match": True,
            "match_case": False,
        },
    }
    try:
        async with session.post(url, json=payload) as resp:
            return await resp.json() if resp.status == 200 else []
    except Exception as e:
        log.error("AnisongDB error: %s", e)
        return []

def _make_link(text: str, url: str | None) -> str:
    if url:
        return f"[{text}]({url})"
    return text

def format_result(song: dict) -> dict:
    anime_name = song.get("animeJPName") or song.get("animeENName") or "N/A"
    mal_id = None
    linked = song.get("linked_ids")
    if linked:
        mal_id = linked.get("myanimelist")
    anime_display = _make_link(anime_name, f"https://myanimelist.net/anime/{mal_id}" if mal_id else None)

    song_name = song.get("songName") or "N/A"
    video = song.get("HQ") or song.get("MQ")
    song_display = _make_link(song_name, f"{MEDIA_URL}/{video}" if video and MEDIA_URL else None)

    artist_name = song.get("songArtist") or "N/A"
    audio = song.get("audio")
    artist_display = _make_link(artist_name, f"{MEDIA_URL}/{audio}" if audio and MEDIA_URL else None)

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