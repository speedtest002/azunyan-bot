import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

class AddRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.amq_guild_id = 1361617403112460389
        
    async def add_role_core(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        embed = discord.Embed(color=discord.Color.red())
        if not interaction.user.guild_permissions.manage_roles:
            embed.description = "Bạn không có quyền dùng lệnh này."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if de_user have that role
        if role in member.roles:
            embed.description = f"{member.mention} đã có role `{role.name}`."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if bot have permission manage_roles
        if not interaction.guild.me.guild_permissions.manage_roles:
            embed.description = "Bot không có quyền `Manage Roles`."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if role is higher than bot's top role
        if role >= interaction.guild.me.top_role:
            embed.description = "Bot không đủ quyền để thêm role này."
            return

        try:
            await member.add_roles(role)
            embed.color = discord.Color.green()
            embed.description = f"Đã thêm role `{role.name}` cho {member.mention}."
            await interaction.response.send_message(embed=embed) # add role
        #except discord.Forbidden:
        #    await interaction.response.send_message("❌ Bot bị từ chối khi thêm role.", ephemeral=True)
        except Exception as e: 
            embed.description = f"Lỗi: `{e}`"
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="add_role", description="Thêm role")
    @app_commands.describe(member="Member", role="Role")
    async def addrole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        # check user have permission
        await self.add_role_core(interaction, member, role)

    @app_commands.command(name="custom_role", description="Tạo role custom (chỉ hỗ trợ server AMQ)")
    @app_commands.describe(name="Tên role", color="Màu role (hex)", icon="Icon")
    async def custom_role(self, interaction: discord.Interaction, name: str, color: str, icon: Optional[discord.Attachment] = None):
        """
        Tạo role custom (chỉ hỗ trợ server AMQ), yêu cầu icon chỉ hỗ trợ png và jpg, kích thước tối thiểu 64x64 và dung lượng không quá 256kb
        """
        #chi ho tro server AMQ
        if interaction.guild.id != self.amq_guild_id:
            return await interaction.response.send_message("Lệnh này chỉ hỗ trợ server ở AMQ", ephemeral=True)
        
        # kiem tra role co ton tai chua
        for role in interaction.guild.roles:
            if role.name == name:
                existing_role = role
                view = discord.ui.View()
                btn_use_this_role = discord.ui.Button(label="Ok!", style=discord.ButtonStyle.primary, custom_id="custom_role_button")
                
                async def button_callback(btn_interaction: discord.Interaction):
                    try:
                        await interaction.user.add_roles(existing_role)
                        await btn_interaction.response.send_message(f"Đã gán role {existing_role.name} cho bạn", ephemeral=True)
                    except Exception as e:
                        await btn_interaction.response.send_message(f"Lỗi khi gán role: {e}", ephemeral=True)
                
                btn_use_this_role.callback = button_callback
                view.add_item(btn_use_this_role)
                return await interaction.response.send_message("Role này đã tồn tại, bạn muốn tự gắn role này chứ?", view=view, ephemeral=True)

        # tao role
        try:
            if "ROLE_ICONS" in interaction.guild.features:
                icon_bytes = await icon.read()
                display_icon=icon_bytes if icon else None
            else:
                display_icon = None
            returned_role = await interaction.guild.create_role(name=name, colour=discord.Color.from_str(color), display_icon=display_icon, permissions=discord.Permissions.none(), mentionable=True)
        except discord.Forbidden:
            await interaction.response.send_message("Bot không đủ quyền để tạo role", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("Đã xảy ra lỗi khi tạo role", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"Đã xảy ra lỗi: {e}", ephemeral=True)
            return
        await interaction.response.send_message(f"Đã tạo role {name} với màu {color}", ephemeral=True)
        # sau do them nguoi dung vao
        await self.add_role_core(interaction=interaction,member=interaction.user, role=returned_role)

async def setup(bot: commands.Bot):
    await bot.add_cog(AddRole(bot))
