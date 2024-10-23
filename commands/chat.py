from discord.ext import commands

class ChatCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="chat")
    async def chat(ctx, *, nội_dung: str):
        """
        Gửi tin nhắn với nội dung

        Parameters:
        ----------
        nội_dung: str
            Nội dung cần gửi
        """
        await ctx.send(f"{nội_dung}")
async def setup(bot):
    await bot.add_cog(ChatCommand(bot))