import discord
from discord import app_commands
from discord.ext import commands

class AddRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add_role", description="Thêm role")
    @app_commands.describe(member="Member", role="Role")
    async def addrole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        # check user have permission
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
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

async def setup(bot: commands.Bot):
    await bot.add_cog(AddRole(bot))
