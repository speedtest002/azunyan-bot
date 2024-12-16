from discord import app_commands, Interaction
from discord.ext import commands

class ChatCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Prefix Command Handler
    @commands.command(name="chat")
    async def chat_prefix(self, ctx, *, message: str):
        await ctx.message.delete()
        await ctx.send(f"{message}")

    # Slash Command
    @app_commands.command(name="chat", description="Gửi tin nhắn với nội dung")
    @app_commands.describe(message="Nội dung cần gửi")
    @app_commands.rename(message="nội_dung")
    async def chat_slash(self, interaction: Interaction, message: str):
        await interaction.response.send_message(f"{message}")

async def setup(bot):
    await bot.add_cog(ChatCommand(bot))