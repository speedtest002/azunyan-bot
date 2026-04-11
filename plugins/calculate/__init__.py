"""plugins/calculate/__init__.py — /calculate và !calculate (!cal, !c, !tinh)"""
import arc
import core.prefix as lightbulb

from plugins.calculate.core import format_result, safe_eval


# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("calculate-slash")

@arc_plugin.include
@arc.slash_command("calculate", "Các phép tính cơ bản (hỗ trợ sqrt, log, sin, cos, tan...)")
async def calculate_slash(
    ctx: arc.GatewayContext,
    expression: arc.Option[str, arc.StrParams("Nhập phép tính (VD: 1+1, sqrt(16)...)")],
    precision: arc.Option[int, arc.IntParams("Số chữ số thập phân", min=0, max=10)] = 4,
) -> None:
    await ctx.respond(format_result(expression, precision))

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.option("expression", "Phép tính cần tính", modifier=lightbulb.GreedyArgument)
@lightbulb.command("calculate", "Tính toán", aliases=["cal", "c", "tinh"])
@lightbulb.implements(lightbulb.PrefixCommand)
async def calculate_prefix(ctx: lightbulb.PrefixContext) -> None:
    expr = " ".join(ctx.options.expression) if isinstance(ctx.options.expression, list) else ctx.options.expression
    result = safe_eval(expr)
    result_str = str(round(result, 4)) if isinstance(result, (int, float)) else str(result)
    await ctx.respond(f"Kết quả: {result_str}")
