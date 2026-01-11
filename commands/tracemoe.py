import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from typing import Optional, List
from urllib.parse import quote


class ResultPaginator(discord.ui.View):  
    def __init__(self, results: List[dict], anilist_data: dict, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.results = results
        self.anilist_data = anilist_data
        self.current_page = 0
        self.max_pages = len(results)
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.max_pages - 1
        self.page_indicator.label = f"{self.current_page + 1}/{self.max_pages}"

    def format_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def create_embed(self) -> discord.Embed:
        result = self.results[self.current_page]
        anilist_id = result.get("anilist")
        anilist_info = self.anilist_data.get(anilist_id) if anilist_id else None
        
        similarity = result.get("similarity", 0) * 100
        from_seconds = result.get("from", 0)
        filename = result.get("filename", "Unknown")
        timestamp = self.format_timestamp(from_seconds)
        
        # Color based on similarity
        if similarity >= 90:
            color = 0x00ff00
        elif similarity >= 70:
            color = 0xffff00
        else:
            color = 0xff0000

        lines = []
        
        if anilist_info:
            titles = anilist_info.get("title", {})
            if titles.get("native"):
                lines.append(f"### {titles['native']}")
            if titles.get("romaji"):
                lines.append(f"### {titles['romaji']}")
            if titles.get("english"):
                lines.append(f"### {titles['english']}")
        
        lines.append(f"`{filename}`")
        lines.append(timestamp)
        lines.append(f"{similarity:.1f}% similarity")
        
        # Add video link
        if result.get("video"):
            lines.append(f"[Preview Video]({result['video']})")

        embed = discord.Embed(description="\n".join(lines), color=color)

        # Set image
        if result.get("image"):
            embed.set_image(url=result["image"])

        embed.set_footer(text=f"Result {self.current_page + 1}/{self.max_pages} | Powered by trace.moe")
        return embed

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.primary, disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


class TraceMoeCommand(commands.Cog):    
    TRACE_MOE_API = "https://api.trace.moe/search"
    ANILIST_API = "https://graphql.anilist.co"
    
    def __init__(self, bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(name="What anime is this?", callback=self.what_anime_context_menu)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def search_anime(self, image_url: str) -> dict:
        async with aiohttp.ClientSession() as session:
            url = f"{self.TRACE_MOE_API}?url={quote(image_url, safe='')}"
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"API error: {response.status}")
                return await response.json()

    async def get_anilist_info(self, anilist_id: int) -> Optional[dict]:
        """Get additional anime info from AniList"""
        query = """
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                title {
                    romaji
                    english
                    native
                }
            }
        }
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.ANILIST_API,
                json={"query": query, "variables": {"id": anilist_id}}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("Media")
        return None

    async def process_search(self, interaction: discord.Interaction, image_url: str):
        await interaction.response.defer(thinking=True)

        try:
            data = await self.search_anime(image_url)
            
            if data.get("error"):
                await interaction.followup.send(f"error: {data['error']}", ephemeral=True)
                return

            results = data.get("result", [])
            if not results:
                await interaction.followup.send("Không có kết quả nào", ephemeral=True)
                return

            results = results[:5]
            
            anilist_ids = set(r.get("anilist") for r in results if r.get("anilist"))
            anilist_data = {}
            for anilist_id in anilist_ids:
                info = await self.get_anilist_info(anilist_id)
                if info:
                    anilist_data[anilist_id] = info

            paginator = ResultPaginator(results, anilist_data)
            embed = paginator.create_embed()
            await interaction.followup.send(embed=embed, view=paginator)

        except Exception as e:
            await interaction.followup.send(f"Đã xảy ra lỗi: {str(e)}", ephemeral=True)

    @app_commands.command(name="whatanime", description="Tìm anime từ screenshot")
    @app_commands.describe(image="Ảnh screenshot")
    async def whatanime(self, interaction: discord.Interaction, image: discord.Attachment):
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.response.send_message("Vui lòng upload file ảnh",ephemeral=True)
            return

        await self.process_search(interaction, image.url)

    async def what_anime_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        image_url = None
        
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                image_url = attachment.url
                break
        
        if not image_url:
            for embed in message.embeds:
                if embed.image:
                    image_url = embed.image.url
                    break
                if embed.thumbnail:
                    image_url = embed.thumbnail.url
                    break

        if not image_url:
            await interaction.response.send_message("Co chac day la anh?", ephemeral=True)
            return

        await self.process_search(interaction, image_url)


async def setup(bot):
    await bot.add_cog(TraceMoeCommand(bot))
