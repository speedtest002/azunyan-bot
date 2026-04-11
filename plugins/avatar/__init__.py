"""plugins/avatar/__init__.py — /avatar và !avatar"""
import arc
import core.prefix as lightbulb
import hikari

from plugins.avatar.core import get_avatar_embed

# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("avatar-slash")

@arc_plugin.include
@arc.slash_command("avatar", "Lấy avatar của người dùng")
async def avatar_slash(
    ctx: arc.GatewayContext,
    user: arc.Option[hikari.User | None, arc.UserParams("Người dùng cần lấy avatar")] = None,
) -> None:
    target = user or ctx.author
    embed = get_avatar_embed(target)
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
@lightbulb.option("user", "Người dùng cần lấy avatar", type=hikari.User, required=False)
@lightbulb.command("avatar", "Lấy avatar của người dùng", aliases=["ava"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def avatar_prefix(ctx: lightbulb.PrefixContext) -> None:
    target = ctx.options.user or ctx.author
    embed = get_avatar_embed(target)
    await ctx.respond(embed=embed)