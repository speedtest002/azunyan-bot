"""plugins/whatanime/__init__.py — /whatanime (slash) + context menu "WAIT: What Anime Is This"""
import aiohttp
import arc
import hikari

from plugins.whatanime.core import build_whatanime_embed

async def _handle_whatanime(ctx, session: aiohttp.ClientSession, image_url: str):
    await ctx.defer()
    embed, error = await build_whatanime_embed(session, image_url)
    if error:
        await ctx.respond(error, flags=hikari.MessageFlag.EPHEMERAL)
    else:
        await ctx.respond(embed=embed)

# ── arc plugin ────────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("whatanime")

@arc_plugin.include
@arc.slash_command("whatanime", "Tìm anime từ screenshot")
async def whatanime_slash(
    ctx: arc.GatewayContext,
    image: arc.Option[hikari.Attachment, arc.AttachmentParams("Ảnh screenshot")],
    session: aiohttp.ClientSession = arc.inject(),
) -> None:
    if not (image.media_type or "").startswith("image/"):
        await ctx.respond("Vui lòng upload file ảnh.", flags=hikari.MessageFlag.EPHEMERAL)
        return
    await _handle_whatanime(ctx, session, image.url)


@arc_plugin.include
@arc.message_command("WAIT: What Anime Is This")
async def whatanime_ctx(
    ctx: arc.GatewayContext,
    message: hikari.Message,
    session: aiohttp.ClientSession = arc.inject(),
) -> None:
    image_url = None
    for att in message.attachments:
        if (att.media_type or "").startswith("image/"):
            image_url = att.url
            break
    if not image_url:
        for embed in message.embeds:
            if embed.image:
                image_url = embed.image.url
                break
            if embed.thumbnail:
                image_url = embed.thumbnail.url
                break
    if not image_url:
        await ctx.respond("Co chac day la anh?", flags=hikari.MessageFlag.EPHEMERAL)
        return
    await _handle_whatanime(ctx, session, image_url)


@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)

@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)