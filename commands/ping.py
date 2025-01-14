from discord.ext import commands

class PingCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx):
        """
        Ping pong ching chong ding dong!
        """
        await ctx.send('Ping is {0} ms'.format(round(self.bot.latency * 1000, 1)))

async def setup(bot):
    await bot.add_cog(PingCommand(bot))