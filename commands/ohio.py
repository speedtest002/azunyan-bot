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
            year = lunar_data['year']
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
        # Set up time
        await self.bot.wait_until_ready()

        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.now(vn_tz)
        #Thời gian
        target_time = now.replace(hour=8, minute=0, second=0, microsecond=0)

        if now > target_time:
            target_time += timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        
        await asyncio.sleep(wait_seconds)

        #Main text part
        text_to_send = (
            f"Ohio!\nHôm nay là {get_day_of_week()}, {get_current_date()},\n"
            f"{get_lunar_date()}\nChúc bạn một ngày tốt lành!\n"
            )
    
        #Quote part
        quote, char_name, title = get_random_vndb_quote()

        if char_name is None:
            description = f'"{quote}"\n\n— {title}'
        else:
            description = f'"{quote}"\n\n— {char_name}, {title}'

        # Create embed for quote
        embed = discord.Embed(
            title=f"Quote of the day:",
            description=description,
            color=0x00ff00
        )

        
        channel_id = 590737241614188563
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(text_to_send)
            await channel.send("https://tenor.com/bPUK1.gif")
            await channel.send(embed=embed)
        else:
            print("Không tìm thấy kênh.")

async def setup(bot):
    await bot.add_cog(Ohio(bot))
