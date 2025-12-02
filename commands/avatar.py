from discord.ext import commands
import discord

class AvatarCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="avatar", description="lấy avatar", aliases=["a", "ava", "avatar"])
    @commands.parameter(name="user", description="Người dùng cần lấy avatar", default=None, type=discord.User)
    async def avatar(self, ctx, user: discord.User = None):
        user = user or ctx.author
        embed = discord.Embed(title=f"Avatar của {user.name}", color=discord.Color.blurple())
        embed.set_image(url=user.avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AvatarCommand(bot))