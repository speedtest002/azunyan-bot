"""plugins/kanji/__init__.py — /kanji và !kanji"""
import aiohttp
import arc
import core.prefix as lightbulb
from core.state import get_app_state

from plugins.kanji.views import kanji_embed

# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("kanji-slash")

@arc_plugin.include
@arc.slash_command("kanji", "Tra cứu chữ Kanji")
async def kanji_slash(
    ctx: arc.GatewayContext,
    kanji: arc.Option[str, arc.StrParams("Chữ Kanji cần tra cứu")],
    session: aiohttp.ClientSession = arc.inject(),
) -> None:
    try:
        result = await kanji_embed(session, kanji)
        if isinstance(result, str):
            await ctx.respond(result)
        else:
            await ctx.respond(embed=result)
    except Exception as e:
        await ctx.respond(f"Lỗi khi fetch data: {e}")

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.option("kanji", "Chữ Kanji cần tra cứu")
@lightbulb.command("kanji", "Tra cứu chữ Kanji", aliases=["k"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def kanji_prefix(ctx: lightbulb.PrefixContext) -> None:
    try:
        state = get_app_state(ctx.app)
        session = state.container.http
        result = await kanji_embed(session, ctx.options.kanji)
        if isinstance(result, str):
            await ctx.respond(result)
        else:
            await ctx.respond(embed=result)
    except Exception as e:
        await ctx.respond(f"Lỗi khi fetch data: {e}")
