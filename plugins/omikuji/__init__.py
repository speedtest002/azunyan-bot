"""plugins/omikuji/__init__.py — /omikuji và !omikuji"""
import arc
import core.prefix as lightbulb

from plugins.omikuji.core import get_omikuji

# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("omikuji-slash")

@arc_plugin.include
@arc.slash_command("omikuji", "Xin xăm đầu năm")
async def omikuji_slash(ctx: arc.GatewayContext) -> None:
    result = get_omikuji(ctx.author.username)
    await ctx.respond(
        f"Bạn đã bốc trúng quẻ **{result}**.\n"
        "Dù có là quẻ gì đi nữa, hãy cố gắng hết mình trong năm nay nhé!"
    )

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.command("omikuji", "Xin xăm đầu năm", aliases=["bocquedaunam"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def omikuji_prefix(ctx: lightbulb.PrefixContext) -> None:
    result = get_omikuji(ctx.author.username)
    await ctx.respond(
        f"Bạn đã bốc trúng quẻ **{result}**.\n"
        "Dù có là quẻ gì đi nữa, hãy cố gắng hết mình trong năm nay nhé!"
    )