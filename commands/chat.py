from discord.ext import commands
from discord import *
class ChatCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name = "chat", description="Gửi tin nhắn với nội dung")
    @app_commands.describe(nội_dung="Nội dung cần gửi")
    async def chat(self, ctx, nội_dung: str):
        await ctx.message.send(nội_dung)

    @commands.command(name="chat")
    async def chat(self, ctx, *noidung):        
        if ctx.author == self.client.user:
            return
        await ctx.message.delete()
        if not noidung:
            return
        else:
            await ctx.channel.send(' '.join(noidung))

async def setup(bot):
    await bot.add_cog(ChatCommand(bot))