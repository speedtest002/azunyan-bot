"""plugins/song/views.py — miru pagination View cho feature /song"""
import hikari
import miru


ITEMS_PER_PAGE = 8


class SongPaginationView(miru.View):
    def __init__(self, results: list, format_func, author_id: int) -> None:
        super().__init__(timeout=3600)
        self.results = results
        self.format_func = format_func
        self.author_id = author_id
        self.current_page = 1
        self.total_pages = max(1, (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.total_pages
        self.page_indicator.label = f"{self.current_page}/{self.total_pages}"

    def create_embed(self) -> hikari.Embed:
        embed = hikari.Embed(
            title="Kết quả tìm kiếm",
            description=f"Tìm thấy {len(self.results)} bài hát",
            color=0x00FF00,
        )
        start = (self.current_page - 1) * ITEMS_PER_PAGE
        for idx, song in enumerate(self.results[start: start + ITEMS_PER_PAGE]):
            fmt = self.format_func(song)
            embed.add_field("Anime" if idx == 0 else "\u200b", fmt["anime"], inline=True)
            embed.add_field("Song Name" if idx == 0 else "\u200b", fmt["song"], inline=True)
            embed.add_field("Artist" if idx == 0 else "\u200b", fmt["artist"], inline=True)
        return embed

    @miru.button(emoji="◀️", style=hikari.ButtonStyle.PRIMARY)
    async def prev_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        if ctx.user.id != self.author_id:
            await ctx.respond("Bạn không có quyền sử dụng nút này.", flags=hikari.MessageFlag.EPHEMERAL)
            return
        self.current_page -= 1
        self._update_buttons()
        await ctx.edit_response(embed=self.create_embed(), components=self)

    @miru.button(label="1/1", style=hikari.ButtonStyle.SECONDARY, disabled=True)
    async def page_indicator(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        pass

    @miru.button(emoji="▶️", style=hikari.ButtonStyle.SUCCESS)
    async def next_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        if ctx.user.id != self.author_id:
            await ctx.respond("Bạn không có quyền sử dụng nút này.", flags=hikari.MessageFlag.EPHEMERAL)
            return
        self.current_page += 1
        self._update_buttons()
        await ctx.edit_response(embed=self.create_embed(), components=self)
