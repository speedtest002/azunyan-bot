import discord
from discord.ext import commands
import requests

class Kanji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def kanji(self, ctx, kanji: str):
        """
        Tìm kanji trong từ điển
        """
        url = "https://mazii.net/api/search/kanji"
        data = {
            "dict": "javi",
            "type": "kanji",
            "query": kanji,
            "page": 1
        }
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()  # Raise an exception for bad status codes
            result = response.json()

            if result.get("status") == 200 and result.get("results"):
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

                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Không tìm thấy kanji {kanji}")

        except requests.exceptions.RequestException as e:
            await ctx.send(f"Lỗi khi fetch data {e}")

def setup(bot):
    bot.add_cog(Kanji(bot))

if __name__ == '__main__':
    import sys
    import io

    # Set stdout to utf-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    import asyncio

    async def test_kanji():
        # Mock context object
        class MockCtx:
            async def send(self, embed):
                print(f"Title: {embed.title}")
                print(f"Description: {embed.description}")
                for field in embed.fields:
                    print(f"{field.name}: {field.value}")

        # Instantiate the Cog and call the command
        cog = Kanji(None)
        await cog.kanji.callback(cog, MockCtx(), "働")

    asyncio.run(test_kanji())