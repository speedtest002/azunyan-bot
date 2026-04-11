"""plugins/chat/__init__.py — /chat và !chat"""
import arc
import core.prefix as lightbulb
import hikari

from .core import send_chat_message

# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("chat-slash")

@arc_plugin.include
@arc.slash_command("chat", "Gửi tin nhắn với nội dung")
async def chat_slash(
    ctx: arc.GatewayContext,
    nội_dung: arc.Option[str, arc.StrParams("Nội dung cần gửi")],
) -> None:
    await ctx.respond("Đã gửi tin nhắn", flags=hikari.MessageFlag.EPHEMERAL)
    await send_chat_message(ctx.get_channel(), nội_dung)  # type: ignore[union-attr]

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()

@lb_loader.command
@lightbulb.option("nội_dung", "Nội dung cần gửi", modifier=lightbulb.GreedyArgument)
@lightbulb.command("chat", "Gửi tin nhắn với nội dung")
@lightbulb.implements(lightbulb.PrefixCommand)
async def chat_prefix(ctx: lightbulb.PrefixContext) -> None:
    content = " ".join(ctx.options.nội_dung) if isinstance(ctx.options.nội_dung, list) else ctx.options.nội_dung
    await ctx.event.message.delete()
    await send_chat_message(ctx.get_channel(), content)