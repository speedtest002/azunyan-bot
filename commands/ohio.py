import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import pytz  # thư viện để xử lý múi giờ
import requests
from dotenv import load_dotenv
import os


vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
now = datetime.now(vn_tz)
channel_id = os.getenv("DISCORD_CHANNEL_ID") 

def get_lunar_date():
    url = "https://open.oapi.vn/date/convert-to-lunar"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "day": now.day,
        "month": now.month,
        "year": now.year,
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        if result.get('code') == 'success':
            lunar_data = result['data']
            day = lunar_data['day']
            month = lunar_data['month']
            cycle = lunar_data['sexagenaryCycle']
            return f"Nhằm ngày {day} tháng {month} năm {cycle}"
        else:
            print("Không lấy được dữ liệu âm lịch:", result.get('message'))
    else:
        print("Lỗi kết nối:", response.status_code, response.text)

def get_day_of_week():
    day_of_week = now.strftime("%A")
    vietnamese_days = {
        "Monday": "thứ Hai",
        "Tuesday": "thứ Ba",
        "Wednesday": "thứ Tư",
        "Thursday": "thứ Năm",
        "Friday": "thứ Sáu",
        "Saturday": "thứ Bảy",
        "Sunday": "Chủ Nhật"
    }
    return vietnamese_days.get(day_of_week, "Không xác định")
def get_current_date():
    day = now.day
    month = now.month
    year = now.year
    return f"ngày {day} tháng {month} năm {year}"

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

class Ohio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.schedule_message())

    async def schedule_message(self):
        await self.bot.wait_until_ready()

        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.now(vn_tz)
        target_time = now.replace(hour=7, minute=30, second=0, microsecond=0)

        if now > target_time:
            target_time += timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # Lấy dữ liệu
        day_of_week = get_day_of_week()
        current_date = get_current_date()
        lunar_date = get_lunar_date()

        quote, char_name, title = get_random_vndb_quote()

        if char_name is None:
            quote_text = f'"{quote}"\n\n— {title}'
        else:
            quote_text = f'"{quote}"\n\n— {char_name}, {title}'

        # Tạo embed
        embed = discord.Embed(
            title="Ohio! Chúc bạn ngày mới tốt lành!",
            description=(
                f"Hôm nay là **{day_of_week}, {current_date}**\n"
                f"Nhằm ngày **{lunar_date}**\n\n"
                f"💬 **Quote of the day:**\n{quote_text}"
            ),
            color=0x00ff00
        )

        # GIF trong embed
        embed.set_image(url="https://files.catbox.moe/v7uyjl.gif")
        channel_id = channel_id
        channel = self.bot.get_channel(channel_id)

        if channel:
            await channel.send(embed=embed)
        else:
            print("Không tìm thấy kênh.")

async def setup(bot):
    await bot.add_cog(Ohio(bot))
