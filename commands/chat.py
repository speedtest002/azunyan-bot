from discord.ext import commands
from discord import *
class ChatCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="chat", description="Gửi tin nhắn với nội dung")
    @app_commands.describe(nội_dung="Nội dung cần gửi")
    async def chat(self, ctx, *, nội_dung):
        await ctx.channel.send(nội_dung)
        # slash command
        if ctx.interaction is not None:
            await ctx.send("Đã gửi tin nhắn", ephemeral=True)
            return  
        # prefix command
        await ctx.message.delete()
        
async def setup(bot):
    await bot.add_cog(ChatCommand(bot))