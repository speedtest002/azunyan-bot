"""plugins/dictionary/__init__.py — /dictionary và !dict (!d)"""
import aiohttp
import arc
import core.prefix as lightbulb
from core.state import get_app_state

from plugins.dictionary.views import dictionary_embed

# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("dictionary-slash")

@arc_plugin.include
@arc.slash_command("dictionary", "Tra từ vựng bằng dictionaryapi.dev")
async def dictionary_slash(
    ctx: arc.GatewayContext,
    word: arc.Option[str, arc.StrParams("Từ cần tra nghĩa")],
    session: aiohttp.ClientSession = arc.inject(),
) -> None:
    embed = await dictionary_embed(session, word)
    await ctx.respond(embed=embed)

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.option("word", "Từ cần tra nghĩa", modifier=lightbulb.GreedyArgument)
@lightbulb.command("dictionary", "Tra từ vựng", aliases=["dict", "d"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def dictionary_prefix(ctx: lightbulb.PrefixContext) -> None:
    word = " ".join(ctx.options.word) if isinstance(ctx.options.word, list) else ctx.options.word
    state = get_app_state(ctx.app)
    session = state.container.http
    result = await dictionary_embed(session, word)
    await ctx.respond(embed=result)
