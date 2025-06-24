import discord
from discord.ext import commands
import requests

def get_random_vndb_quote():
    url = "https://api.vndb.org/kana/quote"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "fields": "vn{id,title},character{id,name},quote",
        "filters": ["random", "=", 1]
    }
    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        print("Lỗi kết nối:", response.status_code, response.text)
        return None

    quote_dict = response.json()
    if not quote_dict.get("results"):
        return "Không có kết quả."

    quote = quote_dict["results"][0]["quote"]
    title = quote_dict["results"][0]["vn"]["title"] 
    character = quote_dict.get("character")
    char_name = character["name"] if character else None

    return quote, char_name, title

class QuoteCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #if you want to make hybrid command, use:
    @commands.hybrid_command(name="quote", description="Get a random Visual novel quote", aliases=["q"])
    async def command_name(self,ctx):

        quote, char_name, title = get_random_vndb_quote()

        if char_name is None:
            description = f'"{quote}"\n\n— {title}'
        else:
            description = f'"{quote}"\n\n— {char_name}, {title}'

        # Create embed
        embed = discord.Embed(
            title=f"Life-changing ahh quote:",
            description=description,
            color=0x00ff00
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(QuoteCommand(bot))