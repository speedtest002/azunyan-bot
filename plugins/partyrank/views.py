"""plugins/partyrank/views.py — miru Modal và Button/View cho Party Rank"""
from __future__ import annotations

import logging
from datetime import datetime

import hikari
import miru

from core.config import API_BASE_URL
from core.state import get_app_state
from plugins.partyrank.core import call_api

logger = logging.getLogger("azunyan.partyrank")


class PRCreateModal(miru.Modal, title="Create New Party Rank"):
    pr_name = miru.TextInput(label="Tên Party Rank", placeholder="Ví dụ: Winter 2024 Anisong")
    pr_slug = miru.TextInput(label="Slug (URL ID)", placeholder="ví dụ: winter-2024")
    pr_desc = miru.TextInput(
        label="Mô tả",
        style=hikari.TextInputStyle.PARAGRAPH,
        required=False,
    )
    deadline = miru.TextInput(
        label="Ngày kết thúc (dd/mm/yyyy-hh:mm:ss) - Giờ UTC",
        placeholder="VD: 31/12/2024-23:59:59",
        required=False,
    )
    echo_msg = miru.TextInput(
        label="Tin nhắn đi kèm",
        style=hikari.TextInputStyle.PARAGRAPH,
        required=False,
        placeholder="VD: @everyone Một Party Rank mới đã xuất hiện!",
    )

    async def callback(self, ctx: miru.ModalContext) -> None:
        try:
            iso_deadline = None
            timestamp = None
            if self.deadline.value:
                try:
                    dt = datetime.strptime(str(self.deadline.value), "%d/%m/%Y-%H:%M:%S")
                    iso_deadline = dt.isoformat() + "Z"
                    timestamp = int(dt.timestamp())
                except ValueError:
                    await ctx.respond("Ngày kết thúc không đúng định dạng dd/mm/yyyy-hh:mm:ss", flags=hikari.MessageFlag.EPHEMERAL)
                    return

            # 1. Tạo thread
            channel = ctx.bot.cache.get_guild_channel(ctx.channel_id)
            if not isinstance(channel, (hikari.TextableGuildChannel,)):
                await ctx.respond("Lệnh này cần được dùng trong kênh văn bản.", flags=hikari.MessageFlag.EPHEMERAL)
                return
            try:
                thread = await ctx.bot.rest.create_thread(
                    channel,
                    hikari.ChannelType.GUILD_PUBLIC_THREAD,
                    f"PR: {self.pr_name.value}",
                )
            except hikari.ForbiddenError:
                await ctx.respond("Bot thiếu quyền 'Create Public Threads'.", flags=hikari.MessageFlag.EPHEMERAL)
                return

            # 2. Gọi API tạo PR
            payload = {
                "slug": str(self.pr_slug.value),
                "name": str(self.pr_name.value),
                "description": str(self.pr_desc.value or ""),
                "created_by_discord_id": str(ctx.user.id),
                "deadline": iso_deadline,
                "discord_guild_id": str(ctx.guild_id),
                "discord_channel_id": str(ctx.channel_id),
                "discord_thread_id": str(thread.id),
            }
            state = get_app_state(ctx.bot)
            session = state.container.http
            data, status = await call_api(session, "/api/party-rank/create", payload)

            if status == 409:
                await thread.delete()
                await ctx.respond("Slug này đã tồn tại, vui lòng chọn slug khác.", flags=hikari.MessageFlag.EPHEMERAL)
                return
            if status not in range(200, 300):
                await thread.delete()
                await ctx.respond(f"Thất bại: {data.get('error', 'Unknown error')}", flags=hikari.MessageFlag.EPHEMERAL)
                return

            # 3. Gửi thông báo + nút Assign
            embed = hikari.Embed(
                title=str(self.pr_name.value),
                description=str(self.pr_desc.value or ""),
                color=0x3489EB,
            )
            if timestamp:
                embed.add_field("Ngày kết thúc", f"<t:{timestamp}:F>")
            embed.add_field("Thread", f"<#{thread.id}>")

            view = AssignView(slug=str(self.pr_slug.value), thread_id=thread.id)
            content = str(self.echo_msg.value) if self.echo_msg.value else "Một Party Rank mới đã được tạo!"
            await ctx.respond(content=content, embed=embed, components=view)

            msg = await ctx.get_last_response()
            miru_client = get_app_state(ctx.bot).miru
            miru_client.start_view(view, bind_to=await msg.retrieve_message())

            base = API_BASE_URL.rstrip("/")
            await ctx.respond(f"Link quản trị: https://{base}/party-rank/{self.pr_slug.value}/master", flags=hikari.MessageFlag.EPHEMERAL)
            await ctx.bot.rest.create_message(thread, content=f"Link tham gia: https://{base}/party-rank/{self.pr_slug.value}/vote")

        except Exception as e:
            logger.error("PRCreateModal error: %s", e, exc_info=True)
            await ctx.respond("Có lỗi xảy ra khi xử lý yêu cầu.", flags=hikari.MessageFlag.EPHEMERAL)


class AssignView(miru.View):
    """Persistent view — nút Assign tham gia Party Rank."""

    def __init__(self, slug: str, thread_id: int) -> None:
        super().__init__(timeout=None)  # persistent
        self.slug = slug
        self.thread_id = thread_id

    @miru.button(label="Assign", style=hikari.ButtonStyle.SUCCESS, custom_id="PR_ASSIGN")
    async def assign_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        payload = {
            "action": "add",
            "discord_id": str(ctx.user.id),
            "discord_username": ctx.user.display_name or ctx.user.username,
            "discord_avatar": str(ctx.user.display_avatar_url),
        }
        state = get_app_state(ctx.bot)
        session = state.container.http
        data, status = await call_api(session, f"/api/party-rank/{self.slug}/master", payload)
        if status in range(200, 300) or status == 409:
            try:
                thread = ctx.bot.cache.get_guild_channel(self.thread_id)
                if thread and isinstance(thread, hikari.GuildThreadChannel):
                    await ctx.bot.rest.add_thread_member(thread, ctx.user)
                    await ctx.respond(f"Đã thêm bạn vào Party Rank và thread <#{self.thread_id}>!", flags=hikari.MessageFlag.EPHEMERAL)
                else:
                    await ctx.respond("Đã tham gia nhưng không tìm thấy thread.", flags=hikari.MessageFlag.EPHEMERAL)
            except Exception as e:
                await ctx.respond(f"Đã tham gia web nhưng không thể add vào thread: {e}", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond(f"Lỗi API: {data.get('error', 'Unknown')}", flags=hikari.MessageFlag.EPHEMERAL)
