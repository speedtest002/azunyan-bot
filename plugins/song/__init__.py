"""plugins/song/__init__.py — /song search, /song search-all (subcommand group) + !song prefix"""
import aiohttp
import arc
import core.prefix as lightbulb
from core.state import get_app_state

from plugins.song.core import build_search_view

async def _handle_search(ctx, session: aiohttp.ClientSession, query: str, dedup: bool, author_id: int, search_type: str = "song"):
    result, view = await build_search_view(session, query, dedup, author_id, search_type)
    if view is None:
        await ctx.respond(result)
        return

    resp = await ctx.respond(embed=result, components=view)
    miru_client = get_app_state(ctx.app if hasattr(ctx, "app") else ctx.client.app).miru
    miru_client.start_view(view, bind_to=await resp.retrieve_message())


# ── arc (slash — subcommand group) ────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("song-slash")
song_group = arc_plugin.include_slash_group("song", "Tìm kiếm bài hát anime")


@song_group.include
@arc.slash_subcommand("search", "Tìm bài hát (lọc trùng)")
async def song_search(
    ctx: arc.GatewayContext,
    query: arc.Option[str, arc.StrParams("Tên bài hát cần tìm")],
    session: aiohttp.ClientSession = arc.inject(),
) -> None:
    await _handle_search(ctx, session, query, True, ctx.author.id)


@song_group.include
@arc.slash_subcommand("search-all", "Tìm bài hát (hiển thị tất cả, kể cả trùng)")
async def song_search_all(
    ctx: arc.GatewayContext,
    query: arc.Option[str, arc.StrParams("Tên bài hát cần tìm")],
    session: aiohttp.ClientSession = arc.inject(),
) -> None:
    await _handle_search(ctx, session, query, False, ctx.author.id)


@song_group.include
@arc.slash_subcommand("search-anime", "Tìm bài hát theo tên anime")
async def song_search_anime(
    ctx: arc.GatewayContext,
    query: arc.Option[str, arc.StrParams("Tên anime cần tìm")],
    session: aiohttp.ClientSession = arc.inject(),
) -> None:
    await _handle_search(ctx, session, query, True, ctx.author.id, "anime")


@song_group.include
@arc.slash_subcommand("search-artist", "Tìm bài hát theo tên nghệ sĩ")
async def song_search_artist(
    ctx: arc.GatewayContext,
    query: arc.Option[str, arc.StrParams("Tên nghệ sĩ cần tìm")],
    session: aiohttp.ClientSession = arc.inject(),
) -> None:
    await _handle_search(ctx, session, query, True, ctx.author.id, "artist")


@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.option("query", "Tên bài hát cần tìm", modifier=lightbulb.GreedyArgument)
@lightbulb.command("song", "Tìm bài hát anime (lọc trùng)", aliases=["s"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def song_prefix(ctx: lightbulb.PrefixContext) -> None:
    query = " ".join(ctx.options.query) if isinstance(ctx.options.query, list) else ctx.options.query
    state = get_app_state(ctx.app)
    session = state.container.http
    await _handle_search(ctx, session, query, True, ctx.author.id)


@lb_loader.command
@lightbulb.option("query", "Tên bài hát cần tìm", modifier=lightbulb.GreedyArgument)
@lightbulb.command("song-all", "Tìm bài hát anime (hiển thị tất cả)", aliases=["sd"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def song_all_prefix(ctx: lightbulb.PrefixContext) -> None:
    query = " ".join(ctx.options.query) if isinstance(ctx.options.query, list) else ctx.options.query
    state = get_app_state(ctx.app)
    session = state.container.http
    await _handle_search(ctx, session, query, False, ctx.author.id)


@lb_loader.command
@lightbulb.option("query", "Tên anime cần tìm", modifier=lightbulb.GreedyArgument)
@lightbulb.command("song-anime", "Tìm bài hát theo tên anime", aliases=["sanime"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def song_anime_prefix(ctx: lightbulb.PrefixContext) -> None:
    query = " ".join(ctx.options.query) if isinstance(ctx.options.query, list) else ctx.options.query
    state = get_app_state(ctx.app)
    session = state.container.http
    await _handle_search(ctx, session, query, True, ctx.author.id, "anime")


@lb_loader.command
@lightbulb.option("query", "Tên nghệ sĩ cần tìm", modifier=lightbulb.GreedyArgument)
@lightbulb.command("song-artist", "Tìm bài hát theo tên nghệ sĩ", aliases=["sartist"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def song_artist_prefix(ctx: lightbulb.PrefixContext) -> None:
    query = " ".join(ctx.options.query) if isinstance(ctx.options.query, list) else ctx.options.query
    state = get_app_state(ctx.app)
    session = state.container.http
    await _handle_search(ctx, session, query, True, ctx.author.id, "artist")