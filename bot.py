import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed
from discord.ui import Button, View, Select
import requests
from PIL import Image
from io import BytesIO
import typing
from datetime import datetime, timedelta
import pytz 
from dotenv import load_dotenv
import os
import json

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False


bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

@bot.hybrid_command(name="ping")
async def chat(ctx):
    """
    Ping pong ding dong!
    """
    await ctx.send('Ping is {0} ms'.format(round(bot.latency*1000, 1)))

@bot.hybrid_command(name="chat")
async def chat(ctx, *, nội_dung: str):
    """
    Gửi tin nhắn với nội dung

    Parameters:
    ----------
    nội_dung: str
        Nội dung cần gửi
    """
    await ctx.send(f"{nội_dung}")

# = snake_commands.Param(name="ngân_hàng", choices=["VietinBank", "Vietcombank", "BIDV", "Agribank", "OCB", "MBBank", "Techcombank", "ACB", "VPBank", "TPBank", "Sacombank", "HDBank", "VietCapitalBank", "SCB", "VIB", "SHB", "Eximbank", "MSB", "CAKE", "Ubank", "Timo", "ViettelMoney", "VNPTMoney", "SaigonBank", "BacABank", "PVcomBank", "Oceanbank", "NCB", "ShinhanBank", "ABBANK", "VietABank", "NamABank", "PGBank", "VietBank", "BaoVietBank", "SeABank", "COOPBANK", "LienVietPostBank", "KienLongBank", "KBank", "KookminHN", "KEBHanaHCM", "KEBHanaHN", "MAFC"]),

@bot.hybrid_command(name = "qr_ngân_hàng")
async def qr_ngân_hàng(
    ctx,
    ngân_hàng: str,
    số_tài_khoản: str,
    số_tiền: str = None, 
    nội_dung: str = None, 
    chủ_tài_khoản: str = None
):
    """
    Tạo mã QR từ số tài khoản ngân hàng

    Parameters
    ----------
    ngân_hàng: str 
        Tên ngân hàng
    số_tài_khoản: str,
        Số tài khoản người nhận
    số_tiền: str = None, 
        Số tiền nhận
    nội_dung: str = None,
        Nội dung chuyển khoản
    chủ_tài_khoản: str = None
        Tên chủ tài khoản
    """
    url = f"https://img.vietqr.io/image/{ngân_hàng}-{số_tài_khoản}-print.png?"
    if số_tiền:
        url += f"amount={số_tiền}"
    if nội_dung:
        nội_dung = nội_dung.replace(" ", "%20")
        url += f"&addInfo={nội_dung}"
    if chủ_tài_khoản:
        chủ_tài_khoản = chủ_tài_khoản.replace(" ", "%20")
        url += f"&accountName={chủ_tài_khoản}"
    await ctx.send(url)

@bot.hybrid_command(name = "qr_ngân_hàng_test")
#@app_commands.command()
async def qr_ngân_hàng_test(
    ctx,
    ngân_hàng: typing.Literal["ACB", "Agribank", "BIDV", "BacABank", "CAKE", "Eximbank", "HDBank", "LienVietPostBank", "MBBank", "OCB", "Oceanbank", "Sacombank", "SaigonBank", "ShinhanBank", "TPBank", "Techcombank", "Timo", "VIB", "VNPTMoney", "VPBank", "VietCapitalBank", "Vietcombank", "VietinBank", "ViettelMoney"],
    số_tài_khoản: str,
    số_tiền: str = None, 
    nội_dung: str = None, 
    chủ_tài_khoản: str = None
):
    """
    Tạo mã QR từ số tài khoản ngân hàng phiên bản 2

    Parameters
    ----------
    ngân_hàng: str 
        Tên ngân hàng
    số_tài_khoản: str,
        Số tài khoản người nhận
    số_tiền: str = None, 
        Số tiền nhận
    nội_dung: str = None,
        Nội dung chuyển khoản
    chủ_tài_khoản: str = None
        Tên chủ tài khoản
    """
    url = f"https://img.vietqr.io/image/{ngân_hàng}-{số_tài_khoản}-print.png?"
    if số_tiền:
        url += f"amount={số_tiền}"
    if nội_dung:
        nội_dung = nội_dung.replace(" ", "%20")
        url += f"&addInfo={nội_dung}"
    if chủ_tài_khoản:
        chủ_tài_khoản = chủ_tài_khoản.replace(" ", "%20")
        url += f"&accountName={chủ_tài_khoản}"
    await ctx.send(url)

##
def calculate_times(current_time, time_to_wakeup=None):
    # Thời gian của một chu kỳ giấc ngủ là 90 phút
    sleep_cycle_duration = timedelta(minutes=90)
    # Thời gian để đi vào giấc ngủ là 14 phút
    time_to_fall_asleep = timedelta(minutes=14)

    if time_to_wakeup:
        # Nếu cung cấp thời gian muốn thức dậy, tính toán thời gian đi ngủ
        wakeup_time = datetime.strptime(time_to_wakeup, '%I:%M %p')
        wakeup_time = current_time.replace(hour=wakeup_time.hour, minute=wakeup_time.minute, second=0, microsecond=0)
        sleep_times = []
        for i in range(6, 2, -1):
            sleep_time = wakeup_time - (i * sleep_cycle_duration) - time_to_fall_asleep
            sleep_duration = i * sleep_cycle_duration
            sleep_times.append({
                'time': sleep_time.strftime('%I:%M %p'),
                'cycles': i,
                'hours': sleep_duration.total_seconds() / 3600
            })
        return sleep_times, "sleep"
    else:
        # Nếu không cung cấp thời gian muốn thức dậy, tính toán thời gian thức dậy
        adjusted_time = current_time + time_to_fall_asleep
        wakeup_times = []
        for i in range(1, 7):
            wakeup_time = adjusted_time + i * sleep_cycle_duration
            sleep_duration = i * sleep_cycle_duration
            wakeup_times.append({
                'time': wakeup_time.strftime('%I:%M %p'),
                'cycles': i,
                'hours': sleep_duration.total_seconds() / 3600
            })
        return wakeup_times, "wakeup"
#sleep
@bot.hybrid_command(name = "sleep")
async def sleep(ctx, giờ_thức_dậy: str = None):
    """
    Tính toán thời gian đi ngủ

    Parameters:
    giờ_thức_dậy: None
        Thời gian mà bạn muốn thức dậy, định dạng: 12:00 AM
    """
    # Lấy thời gian hiện tại theo múi giờ UTC+7
    utc_plus_7 = pytz.timezone('Asia/Bangkok')
    current_time_utc_plus_7 = datetime.now(utc_plus_7)
    
    # Tính toán các thời điểm thức dậy hoặc đi ngủ
    try:
        times, mode = calculate_times(current_time_utc_plus_7, giờ_thức_dậy)
    except ValueError:
        await ctx.send("Định dạng thời gian không hợp lệ! Vui lòng sử dụng định dạng 12 giờ với AM/PM (ví dụ: 07:30 AM hoặc 07:30 PM).")
        return

    if mode == "wakeup":
        result_message = (
            f"Bây giờ là **{current_time_utc_plus_7.strftime('%I:%M %p')}**. Nếu bạn đi ngủ ngay bây giờ, bạn nên cố gắng thức dậy vào một trong những thời điểm sau:\n\n"
        )
        for entry in times:
            result_message += f"⏰ **{entry['time']}** cho {entry['cycles']} chu kỳ - ngủ {entry['hours']:.1f} tiếng.\n"
        
        result_message += "\nXin lưu ý rằng bạn nên đi ngủ vào những thời điểm này. Con người trung bình mất ~14 phút để đi vào giấc ngủ, vì vậy hãy lên kế hoạch cho phù hợp!\n\nChúc ngủ ngon! 😴"
    else:
        result_message = (
            f"Nếu bạn muốn tỉnh giấc vào **{giờ_thức_dậy}**, bạn nên cố gắng đi vào giấc ngủ vào một trong những thời điểm sau:\n\n"
        )
        for entry in times:
            result_message += f"⏰ **{entry['time']}** cho {entry['cycles']} chu kỳ - ngủ {entry['hours']:.1f} tiếng.\n"
        
        result_message += "\nXin lưu ý rằng bạn nên đi ngủ vào những thời điểm này. Con người trung bình mất ~14 phút để đi vào giấc ngủ, vì vậy hãy lên kế hoạch cho phù hợp!\n\nChúc ngủ ngon! 😴"

    # Gửi kết quả về kênh
    await ctx.send(result_message)
"""
#config_ lich chieu
def create_select_options(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        show_count = data.get('total_shows')    
        shows = data.get('shows', [])
        
        options = []
        for show in shows:
            title = show.get('title')
            if title:
                option = discord.SelectOption(
                    label=title[:100],
                    #value=title[:100]  # Trường value có thể được thay thế bằng một giá trị khác nếu cần
                )
                options.append(option)
        
        return options, show_count
    
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from the file {file_path}.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
@bot.hybrid_command(name = "test_select")
async def test_select(ctx):
    list_options, show_count = create_select_options('shows.json')
    select = Select(
        min_values = 1,
        max_values = 25,
        options = list_options
    )
    view = View()
    view.add_item(select)
    await ctx.send("Test select", view = view)
#@bot.hybrid_command(name = "test_button")
#async def test_button(ctx):

total_page = 10
current_page = 1
@bot.hybrid_command(name = "test_button")
async def test_button(ctx):
    next_page = Button(label = f"Trang tiếp ", style = discord.ButtonStyle.green, emoji ="<:Nokotan_Smug:1259094832400302100>")
    index_page = Button(label = f"{current_page}/{total_page}", style = discord.ButtonStyle.grey, disabled = True)
    prev_page = Button(label = f"Trang trước", style = discord.ButtonStyle.blurple, emoji ="<:Nokotan_Smug:1259094832400302100>")
    if(current_page == 1):
        prev_page.disabled = True
    async def next_page_callback(intertraction):
        global current_page
        current_page = current_page + 1
        if(current_page == total_page):
            next_page.disabled = True
        else:
            next_page.disabled = False
        prev_page.disabled = False
        index_page.label = f"{current_page}/{total_page}"
        await intertraction.response.edit_message(content = "next", view = view)
    async def prev_page_callback(intertraction):
        global current_page
        current_page = current_page - 1
        if(current_page == 1):
            prev_page.disabled = True
        else:
            prev_page.disabled = False
        next_page.disabled = False
        index_page.label = f"{current_page}/{total_page}"
        await intertraction.response.edit_message(content = "prev", view = view)

    next_page.callback = next_page_callback
    prev_page.callback = prev_page_callback

    view = View()
    view.add_item(prev_page)
    view.add_item(index_page)
    view.add_item(next_page)

    await ctx.send("test", view = view)
"""

#####test
def create_select_options(file_path, user_id, current_page):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        shows = data.get('shows', [])
        show_count = data.get('total_shows', len(shows))

        try:
            with open('user_selections.json', 'r', encoding='utf-8') as uf:
                user_data = json.load(uf)
        except (FileNotFoundError, json.JSONDecodeError):
            user_data = {}

        user_selections = user_data.get("user_selections", {}).get(user_id, {}).get(f"page_{current_page}", [])

        options = []
        for show in shows:
            title = show.get('title')
            if title:
                option = discord.SelectOption(
                    label=title[:100],
                    value=title[:100],
                    default=title[:100] in user_selections
                )
                options.append(option)

        return options, show_count

    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
        return [], 0
    except json.JSONDecodeError:
        print(f"Error decoding JSON from the file {file_path}.")
        return [], 0
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return [], 0

# Lưu thông tin lựa chọn của người dùng
def save_user_selection(user_id, selected_shows, current_page):
    try:
        with open('user_selections.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"user_selections": {}}

    if user_id not in data["user_selections"]:
        data["user_selections"][user_id] = {}

    data["user_selections"][user_id][f"page_{current_page}"] = selected_shows

    with open('user_selections.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# Tạo view chứa Select và các nút phân trang
async def create_paginated_view(ctx, current_page=1, message=None):
    user_id = str(ctx.author.id)
    list_options, show_count = create_select_options('shows.json', user_id, current_page)
    
    items_per_page = 25
    total_pages = (show_count // items_per_page) + (1 if show_count % items_per_page else 0)
    
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    options = list_options[start_idx:end_idx]

    select = Select(
        min_values=0,
        max_values=len(options),
        placeholder = "Danh sách các phim",
        options=options
    )
    
    next_page = Button(label="Trang tiếp", style=discord.ButtonStyle.green, emoji="<:Nokotan_Smug:1259094832400302100>")
    prev_page = Button(label="Trang trước", style=discord.ButtonStyle.blurple, emoji="<:Nokotan_Smug:1259094832400302100>")
    index_page = Button(label=f"{current_page}/{total_pages}", style=discord.ButtonStyle.grey, disabled=True)

    # Callback cho nút chuyển trang tiếp theo
    async def next_page_callback(interaction):
        await create_paginated_view(ctx, current_page + 1, message=interaction.message)
        await interaction.response.defer()
    
    # Callback cho nút chuyển trang trước đó
    async def prev_page_callback(interaction):
        await create_paginated_view(ctx, current_page - 1, message=interaction.message)
        await interaction.response.defer()
    
    next_page.callback = next_page_callback
    prev_page.callback = prev_page_callback
        
    # Callback cho Select

    async def select_callback(interaction):
        selected_shows = select.values
        save_user_selection(user_id, selected_shows, current_page)
        await interaction.response.send_message(f"Bạn đã chọn: {', '.join(selected_shows)}", ephemeral=True)

    select.callback = select_callback

    if current_page == 1:
        prev_page.disabled = True
    if current_page == total_pages:
        next_page.disabled = True
    
    view = View()
    view.add_item(select)
    view.add_item(prev_page)
    view.add_item(index_page)
    view.add_item(next_page)

    if message:
        await message.edit(content="", view=view)
    else:
        await ctx.send("", view=view)

@bot.hybrid_command(name = "lịch_chiếu_danhsách")
async def lịch_chiếu_danhsách(ctx):
    """
    Chọn các phim cần hiển thị lịch chiếu
    """
    await create_paginated_view(ctx, current_page=1)
###

# lich_chieu
def read_shows(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('timestamp', []), data.get('shows', [])
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from the file {file_path}.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

# Đọc và lọc dữ liệu từ user_selections.json dựa trên user_id
def get_user_selections(user_id):
    try:
        with open('user_selections.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        user_data = data.get("user_selections", {}).get(user_id, {})
        
        selected_titles = []
        for page, titles in user_data.items():
            selected_titles.extend(titles)
        
        return selected_titles
    except FileNotFoundError:
        print("The file user_selections.json was not found.")
        return []
    except json.JSONDecodeError:
        print("Error decoding JSON from the file user_selections.json.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

def convert_to_timestamp(show_time_str):
    utc_plus_7 = pytz.timezone("Asia/Bangkok")
    try:
        show_time = datetime.strptime(show_time_str, "%Y-%m-%d %H:%M:%S")
        show_time = utc_plus_7.localize(show_time)
        timestamp = int(show_time.timestamp())
        return f"<t:{timestamp}:F>"
    except ValueError:
        return show_time_str

async def create_paginated_embeds(ctx, current_page=1, message=None):
    user_id = str(ctx.author.id)
    selected_titles = get_user_selections(user_id)
    timestamp_shows, shows = read_shows('shows.json')

    embeds = []
    for show in shows:
        if show.get('title') in selected_titles:
            embed = discord.Embed(
                title=show.get('title'),
                description=show.get('description'),
                color=discord.Color.blue()
            )
            show_time_str = show.get('show_time')
            show_time_display = convert_to_timestamp(show_time_str) if show_time_str else "N/A"
            embed.add_field(name="Tập mới nhất", value=f"{show.get('lastest_episode')}", inline=True)
            embed.add_field(name="Tập kế tiếp", value=f"{show_time_display}", inline=True)
            embed.set_thumbnail(url=show.get('thumbnail'))
            embed.set_footer(text = f"Cập nhật")
            embed.timestamp = datetime.fromtimestamp(timestamp_shows)
            embeds.append(embed)

    
    items_per_page = 1
    total_pages = (len(embeds) // items_per_page) + (1 if len(embeds) % items_per_page else 0)
    
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_embeds = embeds[start_idx:end_idx]

    next_page = discord.ui.Button(label="Trang tiếp", style=discord.ButtonStyle.green, emoji="<:Nokotan_Smug:1259094832400302100>", row = 1)
    prev_page = discord.ui.Button(label="Trang trước", style=discord.ButtonStyle.blurple, emoji="<:Nokotan_Smug:1259094832400302100>", row = 1)
    index_page = discord.ui.Button(label=f"{current_page}/{total_pages}", style=discord.ButtonStyle.grey, disabled=True, row = 1)

    async def next_page_callback(interaction):
        if interaction.user.id == ctx.author.id:
            await create_paginated_embeds(ctx, current_page + 1, message=interaction.message)
            await interaction.response.defer()
        else:
            await interaction.response.send_message("You do not have permission to use this button.", ephemeral=True)

    async def prev_page_callback(interaction):
        if interaction.user.id == ctx.author.id:
            await create_paginated_embeds(ctx, current_page - 1, message=interaction.message)
            await interaction.response.defer()
        else:
            await interaction.response.send_message("You do not have permission to use this button.", ephemeral=True)

    
    next_page.callback = next_page_callback
    prev_page.callback = prev_page_callback

    if current_page == 1:
        prev_page.disabled = True
    if current_page == total_pages:
        next_page.disabled = True

    view = discord.ui.View()
    view.add_item(prev_page)
    view.add_item(index_page)
    view.add_item(next_page)

    if page_embeds:
        current_title = page_embeds[0].title
        for show in shows:
            if show.get('title') == current_title:
                latest_episode = int(show.get('lastest_episode'))
                for link in show.get('latest_episode_links', []):
                    if link['episode'] == latest_episode:
                        button = Button(label=link['source'], style=discord.ButtonStyle.link, url=link['link'])
                        view.add_item(button)
                break

    if message:
        await message.edit(content=None, embed=page_embeds[0], view=view)
    else:
        await ctx.send(embed=page_embeds[0], view=view)

@bot.hybrid_command(name="lịch_chiếu")
async def lịch_chiếu(ctx):
    """
    Hiển thị lịch chiếu, cần phải chọn các phim cần hiển thị bằng lệnh /lịch_chiếu_danhsách
    """
    await create_paginated_embeds(ctx, current_page=1)
####
load_dotenv()
token = os.getenv('TOKEN')
bot.run(token)
