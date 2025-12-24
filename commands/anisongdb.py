from discord.ext import commands
from discord import app_commands
import discord
import aiohttp
import os

ANISONGDB_URL = os.getenv("ANISONGDB_URL", "")
MEDIA_URL = os.getenv("MEDIA_URL", "")
ITEMS_PER_PAGE = 8  # 8 songs per page (8 * 3 = 24 fields, Discord limit is 25)


class SongPaginationView(discord.ui.View):
    def __init__(self, results, format_func, author_id, timeout=3600):
        super().__init__(timeout=timeout)
        self.results = results
        self.format_func = format_func
        self.author_id = author_id
        self.current_page = 1
        self.total_pages = (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.total_pages
        self.page_indicator.label = f"{self.current_page}/{self.total_pages}"

    def create_embed(self):
        embed = discord.Embed(
            title="Kết quả tìm kiếm",
            description=f"Tìm thấy {len(self.results)} bài hát",
            color=0x00ff00
        )

        start_idx = (self.current_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_results = self.results[start_idx:end_idx]

        for idx, song in enumerate(page_results):
            formatted = self.format_func(song)
            embed.add_field(
                name="Anime" if idx == 0 else "",
                value=formatted["anime"],
                inline=True
            )
            embed.add_field(
                name="Song Name" if idx == 0 else "",
                value=formatted["song"],
                inline=True
            )
            embed.add_field(
                name="Artist" if idx == 0 else "",
                value=formatted["artist"],
                inline=True
            )

        return embed

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không có quyền sử dụng nút này.", ephemeral=True)
            return
        
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.grey, disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.green)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không có quyền sử dụng nút này.", ephemeral=True)
            return
        
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class AnisongDBCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def search_songs(self, query: str, ignore_duplicate: bool = True):
        """
        Call API worker to search for songs.
        """
        url = f"{ANISONGDB_URL}/api/song/search"
        payload = {
            "songNameSearchFilter": {
                "search": query,
                "partialMatch": True
            },
            "andLogic": True,
            "ignoreDuplicate": ignore_duplicate,
            "openingFilter": True,
            "endingFilter": True,
            "insertFilter": True,
            "normalBroadcast": True,
            "dub": True,
            "rebroadcast": True,
            "standard": True,
            "instrumental": True,
            "chanting": True,
            "character": True
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"API Error: {response.status}")
                        return []
        except aiohttp.ClientError as e:
            print(f"HTTP Error: {e}")
            return []
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def format_result(self, song):
        """
        Format a song result for display.
        Returns dict with anime, song, artist display strings.
        """
        # Anime name: prefer Japanese, fallback to English
        anime_name = song.get("animeNameJa") or song.get("animeNameEn") or "N/A"
        mal_id = song.get("malId")
        
        # Create MAL link for anime
        if mal_id:
            anime_display = f"[{anime_name}](https://myanimelist.net/anime/{mal_id})"
        else:
            anime_display = anime_name

        # Song name with video link (hq preferred, fallback to mq)
        song_name = song.get("songName") or "N/A"
        hq = song.get("hq")
        mq = song.get("mq")
        video_file = hq or mq
        
        if video_file and MEDIA_URL:
            song_display = f"[{song_name}]({MEDIA_URL}/{video_file})"
        else:
            song_display = song_name

        # Artist with audio link
        artist_name = song.get("songArtist") or "N/A"
        audio = song.get("audio")
        
        if audio and MEDIA_URL:
            artist_display = f"[{artist_name}]({MEDIA_URL}/{audio})"
        else:
            artist_display = artist_name

        return {
            "anime": anime_display,
            "song": song_display,
            "artist": artist_display
        }

    @commands.hybrid_command(name="song", aliases=["s", "sd"])
    @app_commands.describe(search_query="Tìm kiếm bài hát")
    async def anisongdb(self, ctx, *, search_query: str = ""):
        if not search_query:
            await ctx.send("Vui lòng nhập từ khóa tìm kiếm.")
            return

        ignore_duplicate = ctx.invoked_with != "sd"
        
        results = await self.search_songs(search_query, ignore_duplicate)
        if not results:
            await ctx.send("Không tìm thấy kết quả nào.")
            return

        results.sort(key=lambda x: len(x.get("songName", "")))

        # Create pagination view
        view = SongPaginationView(results, self.format_result, ctx.author.id)
        embed = view.create_embed()
        
        message = await ctx.send(embed=embed, view=view)
        
        # Wait for timeout and disable buttons
        await view.wait()
        try:
            await message.edit(view=view)
        except discord.NotFound:
            pass


async def setup(bot):
    await bot.add_cog(AnisongDBCommand(bot))