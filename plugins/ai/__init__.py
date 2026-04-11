"""plugins/ai/__init__.py — AI plugin router for slash and prefix commands"""
import arc
import hikari
import core.prefix as lightbulb

from plugins.ai.core import process_ai_request, collect_image_urls


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
    
    # Placeholder
    placeholder = hikari.Embed(description="Bot đã ngủm…", color=0xA855F7)
    response = await ctx.respond(embed=placeholder)
    msg = await response.retrieve_message()

    async def edit_fn(embed: hikari.Embed) -> None:
        await msg.edit(embed=embed)

    async def followup_fn(embed: hikari.Embed) -> None:
        await msg.respond(embed=embed)

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
        respond_fn=lambda _: None, # Initial respond already done
        edit_fn=edit_fn,
        followup_fn=followup_fn,
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

    # Placeholder
    placeholder = hikari.Embed(description="Bot đã ngủm…", color=0xA855F7)
    sent = await ctx.respond(embed=placeholder)

    async def edit_fn(embed: hikari.Embed) -> None:
        await sent.edit(embed=embed)

    async def followup_fn(embed: hikari.Embed) -> None:
        await channel.send(embed=embed)

    author_name = ctx.author.username
    member = guild.get_member(ctx.author.id) if guild else None
    if member:
        author_name = member.display_name
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
    )
