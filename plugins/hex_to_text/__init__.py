"""plugins/hex_to_text/__init__.py — Context menu "Hex to text" (slash context menu only)"""
import arc
import hikari

from plugins.hex_to_text.core import decode_hex

# hikari-arc supports message context menus via arc.message_command
arc_plugin = arc.GatewayPlugin("hex-to-text")

@arc_plugin.include
@arc.message_command("Hex to text")
async def hex_to_text_cmd(ctx: arc.GatewayContext, message: hikari.Message) -> None:
    try:
        decoded = decode_hex(message.content or "")
        await ctx.respond(f"Text: {decoded}")
    except Exception:
        await ctx.respond("Co chac day la hex khong?", flags=hikari.MessageFlag.EPHEMERAL)

@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)