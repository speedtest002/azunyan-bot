import discord
from discord.ext import commands
import requests

class Kanji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url = "https://mazii.net/api/search/kanji"

    def fetch_kanji_data(self, kanji):
        """
        Fetch kanji data from the Mazii API.
        """
        data = {
            "dict": "javi",
            "type": "kanji",
            "query": kanji,
            "page": 1
        }
        response = requests.post(self.url, json=data)
        response.raise_for_status()
        return response.json()

    def parse_json_data(self, result):
        """
            Parse the JSON data returned from the Mazii API and create a Discord embed.
        """
        kanji_data = result["results"][0]
        embed = discord.Embed(
            title=f"Kanji: {kanji_data.get('kanji')}",
            description=f"JLPT Level: {kanji_data.get('level')[0] if kanji_data.get('level') else 'N/A'}\nStroke Count: {kanji_data.get('stroke_count', 'N/A')}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Kunyomi", value=kanji_data.get('kun', 'N/A'), inline=False)
        embed.add_field(name="Onyomi", value=kanji_data.get('on', 'N/A'), inline=False)
        embed.add_field(name="Parts", value=", ".join([part['w'] for part in kanji_data.get('compDetail', [])]) if kanji_data.get('compDetail') else 'N/A', inline=False)
        embed.add_field(name="Meaning", value=kanji_data.get('detail', 'N/A'), inline=False)
        embed.add_field(name="Newspaper Frequency Rank", value=kanji_data.get('freq', 'N/A'), inline=False)
        if kanji_data.get('examples'):
            examples = "\n".join([f"{ex['w']} ({ex['p']}): {ex['m']}" for ex in kanji_data['examples']])
            embed.add_field(name="Examples", value=examples, inline=False)
        return embed

    @commands.command(name='kanji', aliases=['k'])
    async def kanji(self, ctx, kanji: str):
        """
        Tìm kanji trong từ điển
        """
        try:
            result = self.fetch_kanji_data(kanji)

            if result.get("status") == 200 and result.get("results"):
                embed = self.parse_json_data(result)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Không tìm thấy kanji {kanji}")

        except requests.exceptions.RequestException as e:
            await ctx.send(f"Lỗi khi fetch data {e}")

async def setup(bot):
    await bot.add_cog(Kanji(bot))