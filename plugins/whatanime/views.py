"""plugins/whatanime/views.py — miru pagination View for anime search results"""
import hikari
import miru

from plugins.whatanime.core import build_result_embed


class WhatAnimeView(miru.View):
    def __init__(self, results: list[dict], anilist_data: dict, author_id: int) -> None:
        super().__init__(timeout=3600)
        self.results = results
        self.anilist_data = anilist_data
        self.author_id = author_id
        self.current_page = 1
        self.total_pages = len(results)
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev.disabled = self.current_page <= 1
        self.next.disabled = self.current_page >= self.total_pages
        self.page_indicator.label = f"{self.current_page}/{self.total_pages}"

    def _build_embed(self) -> hikari.Embed:
        result = self.results[self.current_page - 1]
        anilist_info = self.anilist_data.get(result.get("anilist"))
        return build_result_embed(result, anilist_info, self.current_page, self.total_pages)

    @miru.button(emoji="◀️", style=hikari.ButtonStyle.PRIMARY, custom_id="WA_PREV")
    async def prev(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        if ctx.user.id != self.author_id:
            await ctx.respond("Bạn không có quyền sử dụng nút này.", flags=hikari.MessageFlag.EPHEMERAL)
            return
        self.current_page -= 1
        self._update_buttons()
        await ctx.edit_response(embed=self._build_embed(), components=self)

    @miru.button(label="1/1", style=hikari.ButtonStyle.SECONDARY, disabled=True, custom_id="WA_PAGE")
    async def page_indicator(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        pass

    @miru.button(emoji="▶️", style=hikari.ButtonStyle.SUCCESS, custom_id="WA_NEXT")
    async def next(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        if ctx.user.id != self.author_id:
            await ctx.respond("Bạn không có quyền sử dụng nút này.", flags=hikari.MessageFlag.EPHEMERAL)
            return
        self.current_page += 1
        self._update_buttons()
        await ctx.edit_response(embed=self._build_embed(), components=self)
