"""plugins/sleep/__init__.py — /sleep và !sleep"""
import arc
import core.prefix as lightbulb
from datetime import datetime

from plugins.sleep.core import UTC7, build_response, calculate_times

# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("sleep-slash")

@arc_plugin.include
@arc.slash_command("sleep", "Tính toán thời gian đi ngủ")
async def sleep_slash(
    ctx: arc.GatewayContext,
    giờ_thức_dậy: arc.Option[str | None, arc.StrParams("Giờ muốn thức dậy (VD: 07:30 AM)")] = None,
) -> None:
    now = datetime.now(UTC7)
    try:
        times, mode = calculate_times(now, giờ_thức_dậy)
    except ValueError:
        await ctx.respond("Định dạng thời gian không hợp lệ! Vui lòng dùng định dạng 12 giờ với AM/PM (VD: 07:30 AM).")
        return
    await ctx.respond(build_response(times, mode, giờ_thức_dậy, now))

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.option("giờ_thức_dậy", "Giờ muốn thức dậy (VD: 07:30 AM)", required=False, default=None)
@lightbulb.command("sleep", "Tính toán thời gian đi ngủ", aliases=["ngu", "slip"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def sleep_prefix(ctx: lightbulb.PrefixContext) -> None:
    now = datetime.now(UTC7)
    wakeup = ctx.options.giờ_thức_dậy
    try:
        times, mode = calculate_times(now, wakeup)
    except ValueError:
        await ctx.respond("Định dạng thời gian không hợp lệ! Vui lòng dùng định dạng 12 giờ với AM/PM.")
        return
    await ctx.respond(build_response(times, mode, wakeup, now))