"""plugins/ai/__init__.py — AI plugin router for slash and prefix commands"""
import arc
import hikari
import core.prefix as lightbulb

from plugins.ai.core import process_ai_request, collect_image_urls
from plugins.ai.views import build_ai_embed


# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("ai-slash")

@arc_plugin.include
@arc.slash_command("ai", "gọi nô lệ")
async def ai_slash(
    ctx: arc.GatewayContext,
    prompt: arc.Option[str, arc.StrParams("prompt")],
    attachment: arc.Option[hikari.Attachment | None, arc.AttachmentParams("Ảnh đính kèm")] = None,
) -> None:
    attachments = [attachment] if attachment else []
    image_urls = await collect_image_urls(prompt, attachments=attachments)
    guild = ctx.get_guild()
    channel = ctx.client.app.cache.get_guild_channel(ctx.channel_id) if ctx.channel_id else None

    await ctx.defer()

    first_sent = False

    async def edit_fn(embed: hikari.Embed) -> None:
        nonlocal first_sent
        if not first_sent:
            await ctx.respond(embed=embed)
            first_sent = True
        else:
            await ctx.edit_initial_response(embed=embed)

    async def followup_fn(embed: hikari.Embed) -> None:
        await ctx.respond(embed=embed)

    async def thinking_fn() -> None:
        nonlocal first_sent
        if not first_sent:
            thinking_embed = hikari.Embed(description="✦ Đang suy nghĩ...", color=0xA855F7)
            await ctx.respond(embed=thinking_embed)
            first_sent = True

    author_name = ctx.author.username
    if isinstance(ctx.author, hikari.Member):
        author_name = ctx.author.display_name
    elif hasattr(ctx.author, "global_name") and ctx.author.global_name:
        author_name = ctx.author.global_name

    await process_ai_request(
        prompt=prompt,
        image_urls=image_urls,
        author_name=author_name,
        server_name=guild.name if guild else "DM",
        channel_name=channel.name if hasattr(channel, "name") else "DM",
        respond_fn=lambda _: None,
        edit_fn=edit_fn,
        followup_fn=followup_fn,
        thinking_fn=thinking_fn,
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
@lightbulb.option("prompt", "prompt", modifier=lightbulb.GreedyArgument)
@lightbulb.command("ai", "gọi nô lệ")
@lightbulb.implements(lightbulb.PrefixCommand)
async def ai_prefix(ctx: lightbulb.PrefixContext) -> None:
    prompt = " ".join(ctx.options.prompt) if isinstance(ctx.options.prompt, list) else ctx.options.prompt

    referenced = None
    if ctx.event.message.referenced_message:
        referenced = ctx.event.message.referenced_message

    image_urls = await collect_image_urls(
        prompt,
        attachments=list(ctx.event.message.attachments),
        referenced_message=referenced
    )

    guild = ctx.get_guild()
    channel = ctx.get_channel()

    await ctx.event.message.add_reaction("⏳")

    sent_msg: hikari.Message | None = None

    async def edit_fn(embed: hikari.Embed) -> None:
        nonlocal sent_msg
        if sent_msg is None:
            sent_msg = await ctx.event.message.respond(embed=embed, reply=True)
        else:
            await sent_msg.edit(embed=embed)

    async def followup_fn(embed: hikari.Embed) -> None:
        await channel.send(embed=embed)

    async def thinking_fn() -> None:
        nonlocal sent_msg
        if sent_msg is None:
            thinking_embed = hikari.Embed(description="✦ Đang suy nghĩ...", color=0xA855F7)
            sent_msg = await ctx.event.message.respond(embed=thinking_embed, reply=True)

    author_name = ctx.author.username
    member = guild.get_member(ctx.author.id) if guild else None
    if member:
        author_name = member.display_name
    elif hasattr(ctx.author, "global_name") and ctx.author.global_name:
        author_name = ctx.author.global_name

    try:
        await process_ai_request(
            prompt=prompt,
            image_urls=image_urls,
            author_name=author_name,
            server_name=guild.name if guild else "DM",
            channel_name=channel.name if hasattr(channel, "name") else "DM",
            respond_fn=lambda _: None,
            edit_fn=edit_fn,
            followup_fn=followup_fn,
            thinking_fn=thinking_fn,
        )
    finally:
        await ctx.app.rest.delete_my_reaction(ctx.event.message.channel_id, ctx.event.message.id, "⏳")
