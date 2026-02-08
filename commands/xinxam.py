import discord
from discord.ext import commands
import random
import pytz
from datetime import datetime
import json
import os
import aiohttp
import vnlunar

RENTRY_URL = "https://rentry.co/dientich100quexam"

class XinXamCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fortune_map = {}
        self.load_data()

    def load_data(self):
        try:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            file_path = os.path.join(dir_path, '..', 'data', '100quexam.json') 
            file_path = os.path.abspath(file_path)

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.fortune_map = {str(item['ID']): item for item in data}
        except Exception as e:
            print(f"❌ Lỗi load data xăm: {e}")

    def get_current_lunar_year(self):
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.now(tz)
        lunar_info = vnlunar.get_full_info(now.day, now.month, now.year)
        return lunar_info['can_chi']['year']
    
    @commands.hybrid_command(name="xinxam", description="Xin xăm online")
    async def xinxam(self, ctx):
        await ctx.defer()
        
        lunar_year = self.get_current_lunar_year()
        rng = random.Random(f"{ctx.author.id}-{lunar_year}")
        lucky_number = str(rng.randint(1, 100))
        
        item = self.fortune_map.get(lucky_number, self.fortune_map.get("1")) 

        rank = item.get('Rank', '').upper()

        if "THƯỢNG" in rank:
            embed_color = discord.Color.red()         
        elif "HẠ" in rank:
            embed_color = discord.Color.from_rgb(1, 1, 1) 
        else:
            embed_color = discord.Color.gold()    

        embed = discord.Embed(
            title=f"⛩️ LÁ XĂM SỐ {item['ID']}: {item['Rank']}",
            color=embed_color
        )
        embed.add_field(
            name="📜 Quẻ Thơ",
            value=f"```fix\n{item.get('Original', '')}\n```",
            inline=False
        )

        embed.add_field(
            name="🔤 Phiên Âm",
            value=f"*{item.get('Transliteration', '')}*",
            inline=False
        )
        embed.add_field(
            name="📝 Dịch Thơ",
            value=f"*{item.get('Translation', '')}*",
            inline=False
        )

        embed.add_field(name="💡 Lời Bàn", value=f"┕ {item.get('Comment', '')}", inline=False)

        embed.add_field(name="🔮 Điềm Quẻ", value=f"┕ {item.get('Divination', '')}", inline=False)

        ref_title = item.get('reference_translated', item.get('Reference', 'Tích cổ'))
        ref_detail = item.get('reference_detail', item.get('ReferenceDetail', ''))
        
        if len(ref_detail) > 950:
            ref_value = (
                f"> Nội dung tích cổ này rất dài, vượt quá giới hạn hiển thị.\n"
                f"> 🔗 **[Bấm vào đây để xem toàn bộ điển tích]({RENTRY_URL})**"
            )
        else:
            ref_value = f">>> {ref_detail}" if ref_detail else "Chưa có thông tin."

        embed.add_field(name=f"📖 Tích Cổ: {ref_title}", value=ref_value, inline=False)

        explanation = item.get('Explanation', '')
        if len(explanation) > 950:
            exp_value = f"👉 Nội dung quá dài, xem chi tiết tại: {RENTRY_URL}"
        else:
            exp_value = f"```yaml\n{explanation}\n```"

        embed.add_field(name="🔍 Giải", value=exp_value, inline=False)

        # Footer
        embed.set_footer(
            text=f"Người xin: {ctx.author.display_name} • Năm {lunar_year}", 
            icon_url=ctx.author.display_avatar.url
        )
        embed.timestamp = discord.utils.utcnow()

        await ctx.send(content=f"🏮 **{ctx.author.mention}, đây là quẻ xăm của bạn:**", embed=embed)

async def setup(bot):
    await bot.add_cog(XinXamCommand(bot))