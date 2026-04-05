import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Logging Configuration ---
logger = logging.getLogger('azunyan.partyrank')

# --- Configuration ---
API_BASE_URL = os.getenv("API_BASE_URL")
BOT_SECRET = os.getenv("BOT_SECRET")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID") or 0)

# --- API Helper ---
async def call_partyrank_api(endpoint, payload):
    headers = {
        "Authorization": f"Bearer {BOT_SECRET}",
        "Content-Type": "application/json"
    }
    # Ensure URL is formed correctly without double slashes
    base_url = API_BASE_URL.rstrip('/')
    url = f"https://{base_url}/{endpoint.lstrip('/')}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
                return data, resp.status
    except Exception as e:
        logger.error(f"API call error to {endpoint}: {e}", exc_info=True)
        return {"error": "Internal connection error"}, 500

# --- UI Components ---
class AssignView(discord.ui.View):
    def __init__(self, slug=None, thread_id=None):
        super().__init__(timeout=None)
        if slug and thread_id:
            self.add_item(discord.ui.Button(
                label="Assign", 
                style=discord.ButtonStyle.green, 
                custom_id=f"PR_ASSIGN:{slug}:{thread_id}"
            ))

class PRCreateModal(discord.ui.Modal, title="Create New Party Rank"):
    pr_name = discord.ui.TextInput(label="Tên Party Rank", placeholder="Ví dụ: Winter 2024 Anisong")
    pr_slug = discord.ui.TextInput(label="Slug (URL ID)", placeholder="ví dụ: winter-2024")
    pr_desc = discord.ui.TextInput(label="Mô tả", style=discord.TextStyle.long, required=False)
    deadline = discord.ui.TextInput(label="Ngày kết thúc (dd/mm/yyyy-hh:mm:ss) - Giờ UTC", placeholder="VD: 31/12/2024-23:59:59", required=False)
    echo_msg = discord.ui.TextInput(label="Tin nhắn đi kèm", style=discord.TextStyle.long, required=False, placeholder="VD: @everyone Một Party Rank mới đã xuất hiện!")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse deadline
            iso_deadline = None
            timestamp = None
            if self.deadline.value:
                try:
                    dt = datetime.strptime(str(self.deadline), "%d/%m/%Y-%H:%M:%S")
                    iso_deadline = dt.isoformat() + "Z"
                    timestamp = int(dt.timestamp())
                except ValueError:
                    return await interaction.response.send_message("Ngày kết thúc không đúng định dạng dd/mm/yyyy-hh:mm:ss", ephemeral=True)

            # 1. Tạo thread trước để có ID
            thread = None
            try:
                thread = await interaction.channel.create_thread(
                    name=f"PR: {self.pr_name}",
                    type=discord.ChannelType.public_thread
                )
            except discord.Forbidden:
                logger.error(f"Bot lacks permission to create thread in {interaction.channel.id}")
                return await interaction.response.send_message("Không thể tạo thread do thiếu quyền 'Create Public Threads'.", ephemeral=True)
            except Exception as e:
                logger.error(f"Failed to create thread for PR {self.pr_slug}: {e}", exc_info=True)
                return await interaction.response.send_message("Không thể tạo thread. Vui lòng kiểm tra quyền hạn của Bot.", ephemeral=True)

            # 2. Gọi API tạo PR
            payload = {
                "slug": str(self.pr_slug),
                "name": str(self.pr_name),
                "description": str(self.pr_desc),
                "created_by_discord_id": str(interaction.user.id),
                "deadline": iso_deadline,
                "discord_guild_id": str(interaction.guild_id),
                "discord_channel_id": str(interaction.channel_id),
                "discord_thread_id": str(thread.id)
            }
            data, status = await call_partyrank_api("/api/party-rank/create", payload)

            if status == 409:
                await thread.delete() # Cleanup thread if API failed
                return await interaction.response.send_message("Thất bại: Slug này đã tồn tại, vui lòng chọn slug khác.", ephemeral=True)
            elif status not in range(200, 300):
                await thread.delete() # Cleanup thread if API failed
                logger.warning(f"PR creation failed with status {status}: {data}")
                return await interaction.response.send_message(f"Thất bại: {data.get('error', 'Unknown error')}", ephemeral=True)

            # 3. Gửi tin nhắn kèm nút Assign (Thông báo chính)
            embed = discord.Embed(title=f"{self.pr_name}", description=str(self.pr_desc), color=discord.Color.blue())
            if timestamp:
                embed.add_field(name="Ngày kết thúc", value=f"<t:{timestamp}:F>")
            embed.add_field(name="Thread", value=thread.mention)
            
            view = AssignView(slug=str(self.pr_slug), thread_id=thread.id)
            content = str(self.echo_msg) if self.echo_msg.value else "Một Party Rank mới đã được tạo!"
            
            await interaction.response.send_message(content=content, embed=embed, view=view)
            
            # 4. Gửi link quản trị (ẩn)
            base_url = API_BASE_URL.rstrip('/')
            admin_url = f"https://{base_url}/party-rank/{self.pr_slug}/master"
            await interaction.followup.send(content=f"Link quản trị của bạn: {admin_url}", ephemeral=True)
            
            # 5. Gửi link vote vào thread mới
            vote_url = f"https://{base_url}/party-rank/{self.pr_slug}/vote"
            await thread.send(content=f"Link tham gia: {vote_url}")

        except Exception as e:
            logger.error(f"Unexpected error in PRCreateModal.on_submit: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("Có lỗi xảy ra khi xử lý yêu cầu của bạn.", ephemeral=True)

class PartyRankCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        try:
            if interaction.type == discord.InteractionType.component:
                custom_id = interaction.data.get("custom_id", "")
                if custom_id.startswith("PR_ASSIGN:"):
                    await self.handle_assign_click(interaction, custom_id)
        except Exception as e:
            logger.error(f"Interaction error: {e}", exc_info=True)

    async def handle_assign_click(self, interaction: discord.Interaction, custom_id: str):
        try:
            # Parse slug và thread_id từ custom_id "PR_ASSIGN:slug:thread_id"
            parts = custom_id.split(":")
            if len(parts) < 3: return
            slug, thread_id = parts[1], int(parts[2])

            await interaction.response.defer(ephemeral=True)

            # 1. Gọi API để invite
            payload = {
                "action": "add",
                "discord_id": str(interaction.user.id),
                "discord_username": interaction.user.display_name,
                "discord_avatar": str(interaction.user.display_avatar.url)
            }
            data, status = await call_partyrank_api(f"/api/party-rank/{slug}/master", payload)
            
            if status in range(200, 300) or status == 409:
                # 2. Add vào thread
                try:
                    thread = interaction.guild.get_thread(thread_id) or await interaction.guild.fetch_channel(thread_id)
                    if thread:
                        await thread.add_user(interaction.user)
                        await interaction.followup.send(f"Đã thêm bạn vào Party Rank và thread {thread.mention}!", ephemeral=True)
                    else:
                        await interaction.followup.send("Đã tham gia Party Rank, nhưng không tìm thấy thread cũ để thêm bạn vào.", ephemeral=True)
                except Exception as e:
                    logger.error(f"Failed to add user {interaction.user.id} to thread {thread_id}: {e}", exc_info=True)
                    await interaction.followup.send(f"Đã tham gia web nhưng không thể add vào thread: {e}", ephemeral=True)
            else:
                logger.warning(f"Assign API error for {slug}: Status {status}, Data {data}")
                await interaction.followup.send(f"Lỗi API: {data.get('error', 'Unknown')}", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in handle_assign_click: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("Có lỗi xảy ra khi thực hiện thao tác này.", ephemeral=True)

    @commands.hybrid_command(name="create_pr", description="Tạo một phiên Party Rank mới (Chỉ Admin)")
    async def create_pr(self, ctx: commands.Context):
        try:
            if ctx.author.id != BOT_OWNER_ID:
                return await ctx.send("Bạn không có quyền dùng lệnh này!", ephemeral=True)
            
            # interaction only for send_modal
            if ctx.interaction:
                await ctx.interaction.response.send_modal(PRCreateModal())
            else:
                await ctx.send("Lệnh này chỉ có thể sử dụng dưới dạng slash command.")
        except Exception as e:
            logger.error(f"Error in create_pr command: {e}", exc_info=True)
            await ctx.send("Có lỗi xảy ra khi thực hiện lệnh.")

async def setup(bot):
    await bot.add_cog(PartyRankCommand(bot))
