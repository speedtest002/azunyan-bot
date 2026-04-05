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
        Only include fields that exist and are not empty.
        """
        kanji_data = result["results"][0]
        
        embed = discord.Embed(
            title=f"Kanji: {kanji_data.get('kanji', 'Unknown')}",
            color=discord.Color.blue()
        )
        level = kanji_data.get('level')
        stroke_count = kanji_data.get('stroke_count')
        description_parts = []
        if level and isinstance(level, list) and len(level) > 0:
            description_parts.append(f"JLPT: {level[0]}")
        if stroke_count:
            description_parts.append(f"Số nét: {stroke_count}")
        if description_parts:
            embed.description = "\n".join(description_parts)

        if kanji_data.get('kun'):
            embed.add_field(name="Kunyomi", value=kanji_data['kun'], inline=True)
        if kanji_data.get('on'):
            embed.add_field(name="Onyomi", value=kanji_data['on'], inline=True)
        examples = kanji_data.get("examples")
        if isinstance(examples, list) and len(examples) > 0:
            han_viet = kanji_data.get('mean')
            if han_viet:
                embed.add_field(name="Hán Việt", value=han_viet, inline=True)
        comp_detail = kanji_data.get('compDetail')
        if isinstance(comp_detail, list) and comp_detail:
            parts = [part.get('w') for part in comp_detail if part.get('w')]
            if parts:
                embed.add_field(name="Bộ", value=", ".join(parts), inline=False)
        if kanji_data.get('detail'):
            embed.add_field(name="Nghĩa", value='\n'.join(kanji_data['detail'].split('##')), inline=False)
        if kanji_data.get('freq'):
            embed.add_field(name="Phổ biến thứ", value=kanji_data['freq'], inline=False)
        if isinstance(examples, list) and examples:
            example_list = []
            for ex in examples:
                word = ex.get('w')
                p = ex.get('p')
                m = ex.get('m')
                if word and p and m:
                    ex_str = f"{word} ({p}): {m}"
                    if ex.get('h'):
                        ex_str += f" ({ex['h']})"
                    example_list.append(ex_str)
            if example_list:
                embed.add_field(name="Ví dụ", value="\n".join(example_list), inline=False)

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