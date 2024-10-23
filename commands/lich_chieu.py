import discord
from discord.ext import commands
from discord.ui import *
from discord import *
import json
import datetime
import pytz

class LichChieuCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def create_select_options(self, file_path, user_id, current_page):
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
    def save_user_selection(self, user_id, selected_shows, current_page):
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
    async def create_paginated_view(self, ctx, current_page=1, message=None):
        user_id = str(ctx.author.id)
        list_options, show_count = self.create_select_options('shows.json', user_id, current_page)
        
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
        
        next_page = Button(label="Trang sau", style=discord.ButtonStyle.green, emoji="<:Nokotan_Smug:1259094832400302100>")
        prev_page = Button(label="Trang trước", style=discord.ButtonStyle.blurple, emoji="<:Nokotan_Smug:1259094832400302100>")
        index_page = Button(label=f"{current_page}/{total_pages}", style=discord.ButtonStyle.grey, disabled=True)

        # Callback cho nút chuyển trang tiếp theo
        async def next_page_callback(interaction):
            await self.create_paginated_view(ctx, current_page + 1, message=interaction.message, ephemeral=True)
            await interaction.response.defer()
        
        # Callback cho nút chuyển trang trước đó
        async def prev_page_callback(interaction):
            await self.create_paginated_view(ctx, current_page - 1, message=interaction.message, ephemeral=True)
            await interaction.response.defer()
        
        next_page.callback = next_page_callback
        prev_page.callback = prev_page_callback
            
        # Callback cho Select

        async def select_callback(interaction):
            selected_shows = select.values
            self.save_user_selection(user_id, selected_shows, current_page)
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

    @commands.hybrid_command(name = "lịch_chiếu_danh_sách", aliases = ['lichchieu_danhsach', 'lc_ds'])
    async def lịch_chiếu_danhsách(self, ctx):
        """
        Chọn các phim cần hiển thị lịch chiếu
        """
        await self.create_paginated_view(ctx, current_page=1)
    ###

    # lich_chieu
    def read_shows(self, file_path):
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
    def get_user_selections(self, user_id):
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

    def convert_to_timestamp(self, show_time_str):
        utc_plus_7 = pytz.timezone("Asia/Bangkok")
        try:
            show_time = datetime.strptime(show_time_str, "%Y-%m-%d %H:%M:%S")
            show_time = utc_plus_7.localize(show_time)
            timestamp = int(show_time.timestamp())
            return f"<t:{timestamp}:F>"
        except ValueError:
            return show_time_str

    async def create_paginated_embeds(self, ctx, current_page=1, message=None):
        user_id = str(ctx.author.id)
        selected_titles = self.get_user_selections(user_id)
        timestamp_shows, shows = self.read_shows('shows.json')

        if not selected_titles:
            await ctx.send("Bạn chưa chọn phim cần hiện, hãy sử dụng lệnh `/lịch_chiếu_danhsách` để chọn phim.", ephemeral=True)
            return

        embeds = []
        button_data = []
        for show in shows:
            if show.get('title') in selected_titles:
                # Create the embed
                embed = discord.Embed(
                    title=show.get('title'),
                    description=show.get('description'),
                    color=discord.Color.blue()
                )
                show_time_str = show.get('show_time')
                show_time_display = self.convert_to_timestamp(show_time_str) if show_time_str else "N/A"
                embed.set_thumbnail(url=show.get('thumbnail'))
                embed.set_footer(text="Cập nhật")
                embed.timestamp = datetime.fromtimestamp(timestamp_shows)
                embeds.append(embed)

                # Determine button links and episode info
                episode_links = show.get('latest_episode_links', [])
                latest_episode = show.get('lastest_episode')

                # Find the maximum episode number for each source
                source_max_episodes = {}
                for link in episode_links:
                    source = link['source']
                    episode = link['episode']
                    if source not in source_max_episodes or episode > source_max_episodes[source]['episode']:
                        source_max_episodes[source] = link
                
                # Determine the value for the latest episode
                if latest_episode is not None:
                    latest_episode_value = latest_episode
                else:
                    # Use the maximum episode from the sources if lastest_episode is not available
                    max_episode = max((link['episode'] for link in source_max_episodes.values()), default='N/A')
                    latest_episode_value = max_episode

                embed.add_field(name="Tập mới nhất", value=f"{latest_episode_value}", inline=True)
                embed.add_field(name="Tập kế tiếp", value=f"{show_time_display}", inline=True)
                # Determine button links
                if latest_episode is not None:
                    # Add buttons for the latest episode link
                    buttons = [
                        Button(label=link['source'], style=discord.ButtonStyle.link, url=link['link'])
                        for link in episode_links if link['episode'] == latest_episode
                    ]
                else:
                    # Add buttons for the max episode of each source
                    buttons = [
                        Button(label=link['source'], style=discord.ButtonStyle.link, url=link['link'])
                        for link in source_max_episodes.values()
                    ]
                
                button_data.append(buttons)


        
        items_per_page = 1
        total_pages = (len(embeds) // items_per_page) + (1 if len(embeds) % items_per_page else 0)
        
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_embeds = embeds[start_idx:end_idx]
        current_buttons = button_data[start_idx:end_idx]

        next_page = discord.ui.Button(label="Trang tiếp", style=discord.ButtonStyle.green, emoji="<:Nokotan_Smug:1259094832400302100>", row = 1)
        prev_page = discord.ui.Button(label="Trang trước", style=discord.ButtonStyle.blurple, emoji="<:Nokotan_Smug:1259094832400302100>", row = 1)
        index_page = discord.ui.Button(label=f"{current_page}/{total_pages}", style=discord.ButtonStyle.grey, disabled=True, row = 1)

        async def next_page_callback(interaction):
            if interaction.user.id == ctx.author.id:
                await self.create_paginated_embeds(ctx, current_page + 1, message=interaction.message)
                await interaction.response.defer()
            else:
                await interaction.response.send_message("You do not have permission to use this button.", ephemeral=True)

        async def prev_page_callback(interaction):
            if interaction.user.id == ctx.author.id:
                await self.create_paginated_embeds(ctx, current_page - 1, message=interaction.message)
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
        if current_buttons:
            for button in current_buttons[0]:
                view.add_item(button)
        
        if message:
            await message.edit(content=None, embed=page_embeds[0], view=view)
        else:
            await ctx.send(embed=page_embeds[0], view=view)

    @commands.hybrid_command(name="lịch_chiếu", aliases = ['lc', 'lichchieu'])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def lịch_chiếu(self, ctx):
        """
        Hiển thị lịch chiếu, cần phải chọn các phim cần hiển thị bằng lệnh /lịch_chiếu_danhsách
        """
        await self.create_paginated_embeds(ctx, current_page=1)

async def setup(bot):
    await bot.add_cog(LichChieuCommand(bot))