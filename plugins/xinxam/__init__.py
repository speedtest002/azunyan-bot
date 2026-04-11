"""plugins/xinxam/__init__.py — /xinxam và !xinxam"""
import arc
import core.prefix as lightbulb

from plugins.xinxam.core import build_xinxam_embed

# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("xinxam-slash")

@arc_plugin.include
@arc.slash_command("xinxam", "Xin xăm online")
async def xinxam_slash(ctx: arc.GatewayContext) -> None:
    await ctx.defer()
    embed = build_xinxam_embed(ctx.author.id, ctx.author.display_name, str(ctx.author.display_avatar_url))
    await ctx.respond(content=f"🏮 **{ctx.author.mention}, đây là quẻ xăm của bạn:**", embed=embed)

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.command("xinxam", "Xin xăm online")
@lightbulb.implements(lightbulb.PrefixCommand)
async def xinxam_prefix(ctx: lightbulb.PrefixContext) -> None:
    embed = build_xinxam_embed(ctx.author.id, ctx.author.display_name, str(ctx.author.display_avatar_url))
    await ctx.respond(content=f"🏮 **{ctx.author.mention}, đây là quẻ xăm của bạn:**", embed=embed)