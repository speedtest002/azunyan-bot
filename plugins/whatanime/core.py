import aiohttp
import hikari
import logging
from urllib.parse import quote

log = logging.getLogger("azunyan.whatanime")

TRACE_MOE_API = "https://api.trace.moe/search"
ANILIST_API = "https://graphql.anilist.co"

async def search_anime(session: aiohttp.ClientSession, image_url: str) -> dict:
    async with session.get(f"{TRACE_MOE_API}?url={quote(image_url, safe='')}") as resp:
        if resp.status != 200:
            raise RuntimeError(f"API error: {resp.status}")
        return await resp.json()

async def get_anilist_info(session: aiohttp.ClientSession, anilist_id: int) -> dict | None:
    query = """query ($id: Int) { Media(id: $id, type: ANIME) { title { romaji english native } } }"""
    async with session.post(ANILIST_API, json={"query": query, "variables": {"id": anilist_id}}) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("data", {}).get("Media")
    return None

def _fmt_ts(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

async def build_whatanime_embed(session: aiohttp.ClientSession, image_url: str) -> tuple[hikari.Embed | None, str | None]:
    try:
        data = await search_anime(session, image_url)
        if data.get("error"):
            return None, f"Lỗi: {data['error']}"

        results = [r for r in data.get("result", []) if r.get("similarity", 0) * 100 > 70][:5]
        if not results:
            return None, "Không có kết quả."

        anilist_ids = {r.get("anilist") for r in results if r.get("anilist")}
        anilist_data = {}
        for aid in anilist_ids:
            info = await get_anilist_info(session, aid)
            if info:
                anilist_data[aid] = info

        # Send first result (pagination can be added later with miru)
        result = results[0]
        anilist_info = anilist_data.get(result.get("anilist"))
        sim = result.get("similarity", 0) * 100

        lines = []
        if anilist_info:
            titles = anilist_info.get("title", {})
            for k in ("native", "romaji", "english"):
                if titles.get(k):
                    lines.append(f"### {titles[k]}")
        lines.append(f"`{result.get('filename', 'Unknown')}`")
        lines.append(_fmt_ts(result.get("from", 0)))
        lines.append(f"{sim:.1f}% similarity")
        if result.get("video"):
            lines.append(f"[Preview Video]({result['video']})")

        color = 0x00FF00 if sim >= 90 else (0xFFFF00 if sim >= 70 else 0xFF0000)
        embed = hikari.Embed(description="\n".join(lines), color=color)
        if result.get("image"):
            embed.set_image(result["image"])
        embed.set_footer(text=f"Result 1/{len(results)} | Powered by trace.moe")

        return embed, None
    except Exception as e:
        return None, f"Đã xảy ra lỗi: {e}"