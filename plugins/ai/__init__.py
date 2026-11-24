"""plugins/ai/__init__.py — AI plugin router for slash and prefix commands"""
from __future__ import annotations

import logging
import re

import aiohttp
import arc
import hikari
import miru

import core.prefix as lightbulb
from core.state import get_app_state
from plugins.ai.core import close_ai_client, collect_image_urls, process_ai_request
from plugins.ai.views import AIPaginationView

log = logging.getLogger("azunyan.ai")

_MAX_REPLY_CONTEXT_LEN = 1500


async def _on_bot_stopping(_: hikari.StoppingEvent) -> None:
    await close_ai_client()


def _extract_raw_prefix_prompt(
    content: str,
    prefix: str,
    command_names: tuple[str, ...],
) -> str:
    """Extract raw prompt text from message content while preserving newlines, quotes, and backslashes."""
    if not content or not content.startswith(prefix):
        return ""
    body = content.removeprefix(prefix).lstrip()
    names_pattern = "|".join(re.escape(n) for n in sorted(command_names, key=len, reverse=True))
    match = re.match(rf"^(?:{names_pattern})(?:\s+|$)", body, re.IGNORECASE)
    if not match:
        return ""
    return body[match.end() :].strip()


def _resolve_author_name(
    author: hikari.User,
    guild: hikari.GatewayGuild | None = None,
) -> str:
    if isinstance(author, hikari.Member):
        return author.display_name
    if guild is not None:
        member = guild.get_member(author.id)
        if member is not None:
            return member.display_name
    global_name = getattr(author, "global_name", None)
    return global_name or author.username


async def _resolve_referenced_message(ctx: lightbulb.PrefixContext) -> hikari.Message | None:
    msg = ctx.event.message
    if msg.referenced_message is not None:
        return msg.referenced_message

    ref = msg.message_reference
    if ref is None or ref.id is None:
        return None

    ref_channel_id = ref.channel_id or msg.channel_id
    try:
        return await ctx.app.rest.fetch_message(ref_channel_id, ref.id)
    except Exception as exc:
        log.debug("Could not fetch referenced message %s: %s", ref.id, exc)
        return None


def _attach_reply_context(prompt: str, referenced: hikari.Message | None) -> str:
    if referenced is None or not referenced.content:
        return prompt
    ref_text = referenced.content.strip()
    if not ref_text:
        return prompt
    if len(ref_text) > _MAX_REPLY_CONTEXT_LEN:
        ref_text = ref_text[:_MAX_REPLY_CONTEXT_LEN] + "…"
    ref_author = getattr(referenced.author, "global_name", None) or referenced.author.username
    context_block = f"[Đang trả lời tin nhắn của {ref_author}]:\n{ref_text}"
    if prompt:
        return f"{context_block}\n\n[Yêu cầu]:\n{prompt}"
    return context_block


# ── arc (slash) ──────────────────────────────────────────────────────────────
arc_plugin = arc.GatewayPlugin("ai-slash")


@arc_plugin.include
@arc.slash_command("ai", "gọi nô lệ")
async def ai_slash(
    ctx: arc.GatewayContext,
    prompt: arc.Option[str, arc.StrParams("prompt")],
    attachment: arc.Option[hikari.Attachment | None, arc.AttachmentParams("Ảnh đính kèm")] = None,
    miru_client: miru.Client = arc.inject(),
    http_session: aiohttp.ClientSession = arc.inject(),
) -> None:
    # Defer ngay lập tức trước mọi thao tác I/O để tránh quá hạn 3s của Discord
    await ctx.defer()

    attachments = [attachment] if attachment else []
    image_urls = await collect_image_urls(prompt, attachments=attachments)
    guild = ctx.get_guild()
    channel = ctx.client.app.cache.get_guild_channel(ctx.channel_id) if ctx.channel_id else None

    async def edit_fn(embed: hikari.Embed, components=None) -> None:
        kwargs = {"embed": embed}
        if components is not None:
            kwargs["components"] = components
        await ctx.edit_initial_response(**kwargs)

    async def followup_fn(embed: hikari.Embed, components=None) -> None:
        kwargs = {"embed": embed}
        if components is not None:
            kwargs["components"] = components
        await ctx.respond(**kwargs)

    async def thinking_fn(status_text: str = "✦ Đang suy nghĩ...") -> None:
        thinking_embed = hikari.Embed(description=status_text, color=0xA855F7)
        await ctx.edit_initial_response(embed=thinking_embed)

    async def paginate_fn(view: AIPaginationView) -> None:
        embed = view._build_embed()
        resp = await ctx.edit_initial_response(embed=embed, components=view)
        msg = await resp.retrieve_message()
        miru_client.start_view(view, bind_to=msg)

    author_name = _resolve_author_name(ctx.author, guild)
    if guild is not None:
        server_name = guild.name
    elif ctx.guild_id is not None:
        server_name = f"External Server ({ctx.guild_id})"
    else:
        server_name = "DM"

    await process_ai_request(
        prompt=prompt,
        image_urls=image_urls,
        author_name=author_name,
        server_name=server_name,
        channel_name=channel.name if channel and hasattr(channel, "name") else "DM",
        edit_fn=edit_fn,
        followup_fn=followup_fn,
        thinking_fn=thinking_fn,
        author_id=ctx.author.id,
        guild_id=ctx.guild_id,
        channel_id=ctx.channel_id,
        paginate_fn=paginate_fn,
        http_session=http_session,
    )


@arc.loader
def arc_loader(client: arc.GatewayClient) -> None:
    client.add_plugin(arc_plugin)
    client.app.event_manager.subscribe(hikari.StoppingEvent, _on_bot_stopping)


@arc.unloader
def arc_unloader(client: arc.GatewayClient) -> None:
    client.remove_plugin(arc_plugin)
    client.app.event_manager.unsubscribe(hikari.StoppingEvent, _on_bot_stopping)


# ── lightbulb (prefix) ───────────────────────────────────────────────────────
lb_loader = lightbulb.Loader()


@lb_loader.command
@lightbulb.option("prompt", "prompt", required=False, default="", modifier=lightbulb.GreedyArgument)
@lightbulb.command("ai", "gọi nô lệ")
@lightbulb.implements(lightbulb.PrefixCommand)
async def ai_prefix(ctx: lightbulb.PrefixContext) -> None:
    raw_prompt = _extract_raw_prefix_prompt(
        ctx.event.content or "",
        ctx.prefix,
        (ctx.command.name, *ctx.command.aliases),
    )
    if not raw_prompt and ctx.options.prompt:
        raw_prompt = (
            " ".join(ctx.options.prompt)
            if isinstance(ctx.options.prompt, list)
            else str(ctx.options.prompt)
        ).strip()

    referenced = await _resolve_referenced_message(ctx)
    image_urls = await collect_image_urls(
        raw_prompt,
        attachments=list(ctx.event.message.attachments),
        referenced_message=referenced,
    )
    prompt = _attach_reply_context(raw_prompt, referenced)

    if not prompt and not image_urls:
        await ctx.event.message.respond(
            "Vui lòng nhập câu hỏi hoặc đính kèm/trả lời một ảnh.",
            reply=True,
            reply_must_exist=False,
        )
        return

    guild = ctx.get_guild()
    channel = ctx.get_channel()
    state = get_app_state(ctx.app)
    http_session = state.container.http if state.container else None

    reaction_added = False
    try:
        await ctx.event.message.add_reaction("⏳")
        reaction_added = True
    except hikari.HTTPError as exc:
        log.debug("Could not add reaction to message %s: %s", ctx.event.message.id, exc)

    sent_msg: hikari.Message | None = None

    async def edit_fn(embed: hikari.Embed, components=None) -> None:
        nonlocal sent_msg
        kwargs = {"embed": embed}
        if components is not None:
            kwargs["components"] = components
        if sent_msg is None:
            sent_msg = await ctx.event.message.respond(
                **kwargs,
                reply=True,
                reply_must_exist=False,
            )
        else:
            await sent_msg.edit(**kwargs)

    async def followup_fn(embed: hikari.Embed, components=None) -> None:
        kwargs = {"embed": embed}
        if components is not None:
            kwargs["components"] = components
        await channel.send(**kwargs)

    async def thinking_fn(status_text: str = "✦ Đang suy nghĩ...") -> None:
        nonlocal sent_msg
        thinking_embed = hikari.Embed(description=status_text, color=0xA855F7)
        if sent_msg is None:
            sent_msg = await ctx.event.message.respond(
                embed=thinking_embed,
                reply=True,
                reply_must_exist=False,
            )
        else:
            await sent_msg.edit(embed=thinking_embed)

    async def paginate_fn(view: AIPaginationView) -> None:
        nonlocal sent_msg
        embed = view._build_embed()
        if sent_msg is None:
            sent_msg = await ctx.event.message.respond(
                embed=embed,
                components=view,
                reply=True,
                reply_must_exist=False,
            )
        else:
            sent_msg = await sent_msg.edit(embed=embed, components=view)
        state.miru.start_view(view, bind_to=sent_msg)

    author_name = _resolve_author_name(ctx.author, guild)

    try:
        await process_ai_request(
            prompt=prompt,
            image_urls=image_urls,
            author_name=author_name,
            server_name=guild.name if guild else "DM",
            channel_name=channel.name if hasattr(channel, "name") else "DM",
            edit_fn=edit_fn,
            followup_fn=followup_fn,
            thinking_fn=thinking_fn,
            author_id=ctx.author.id,
            guild_id=ctx.event.message.guild_id,
            channel_id=ctx.event.message.channel_id,
            paginate_fn=paginate_fn,
            http_session=http_session,
        )
    finally:
        if reaction_added:
            try:
                await ctx.app.rest.delete_my_reaction(
                    ctx.event.message.channel_id,
                    ctx.event.message.id,
                    "⏳",
                )
            except hikari.HTTPError:
                pass
