"""plugins/ping/__init__.py — /ping và !ping"""
import arc
import core.prefix as lightbulb

from plugins.ping.core import get_ping_message

# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("ping-slash")

@arc_plugin.include
@arc.slash_command("ping", "Ping pong ding dong!")
async def ping_slash(ctx: arc.GatewayContext) -> None:
    msg = get_ping_message(ctx.client.app.heartbeat_latency)
    await ctx.respond(msg)

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.command("ping", "Ping pong ding dong!")
@lightbulb.implements(lightbulb.PrefixCommand)
async def ping_prefix(ctx: lightbulb.PrefixContext) -> None:
    msg = get_ping_message(ctx.app.heartbeat_latency)
    await ctx.respond(msg)