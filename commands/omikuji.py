from discord import *
from discord.ext import commands
import random
from datetime import datetime, timedelta
import pytz

class OmikujiCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="omikuji", aliases=["bocquedaunam"])
    async def omikuji(self,ctx):
        def get_omikuji(user_name):
            list_omikuji = ["Đại Cát", "Trung Cát", "Tiểu Cát", "Cát", "Bán Cát", "Mạt Cát","Mạt Tử Cát", "Hung", "Tiểu Hung", "Bán Hung", "Mạt Hung", "Đại Hung"]
            random.seed(user_name + str(datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).year))
            omikuji = random.choice(list_omikuji)
            return omikuji
        await ctx.send(f"Bạn đã bốc trúng quẻ {get_omikuji(ctx.author.name)}.\nDù có là quẻ gì đi nữa, hãy cố gắng hết mình trong năm nay nhé!")
    
async def setup(bot):
    await bot.add_cog(OmikujiCommand(bot))