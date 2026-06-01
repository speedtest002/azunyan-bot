"""plugins/ai/views.py — UI components and embed builders for AI plugin"""
from __future__ import annotations

import hikari
import miru


class AIPaginationView(miru.View):
    def __init__(self, pages: list[str], model_name: str, tokens: int,
                 sources: set[tuple[str, str]], author_id: int) -> None:
        super().__init__(timeout=3600)
        self.pages = pages
        self.model_name = model_name
        self.tokens = tokens
        self.author_id = author_id
        self.current_page = 1
        self.total_pages = len(pages)

        source_buttons = [miru.LinkButton(label=title[:80], url=url) for title, url in list(sources)[:20]]
        for btn in source_buttons:
            self.add_item(btn)
        for i, btn in enumerate(source_buttons):
            btn._rendered_row = 1 + (i // 5)

        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev.disabled = self.current_page <= 1
        self.next.disabled = self.current_page >= self.total_pages
        self.page_indicator.label = f"{self.current_page}/{self.total_pages}"

    def _build_embed(self) -> hikari.Embed:
        page_text = self.pages[self.current_page - 1]
        display = page_text if len(page_text) <= 4000 else page_text[:4000]
        embed = hikari.Embed(description=display or "…", color=0x57F287)
        embed.set_footer(f"{self.model_name} | {self.tokens} tokens ({self.current_page}/{self.total_pages})")
        return embed

    @miru.button(emoji="◀️", style=hikari.ButtonStyle.PRIMARY, custom_id="AI_PREV")
    async def prev(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        if ctx.user.id != self.author_id:
            await ctx.respond("Bạn không có quyền sử dụng nút này.", flags=hikari.MessageFlag.EPHEMERAL)
            return
        self.current_page -= 1
        self._update_buttons()
        await ctx.edit_response(embed=self._build_embed(), components=self)

    @miru.button(label="1/1", style=hikari.ButtonStyle.SECONDARY, disabled=True, custom_id="AI_PAGE")
    async def page_indicator(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        pass

    @miru.button(emoji="▶️", style=hikari.ButtonStyle.SUCCESS, custom_id="AI_NEXT")
    async def next(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        if ctx.user.id != self.author_id:
            await ctx.respond("Bạn không có quyền sử dụng nút này.", flags=hikari.MessageFlag.EPHEMERAL)
            return
        self.current_page += 1
        self._update_buttons()
        await ctx.edit_response(embed=self._build_embed(), components=self)


def split_text(text: str, max_len: int = 4000) -> list[str]:
    """Splits text into chunks of max_len, attempting to break at newlines."""
    parts, current = [], ""
    for line in text.split("\n"):
        if len(line) > max_len:
            if current:
                parts.append(current)
                current = ""
            for i in range(0, len(line), max_len):
                parts.append(line[i: i + max_len])
            continue
        if len(current) + len(line) + 1 > max_len:
            parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)
    return parts


def build_ai_embed(text: str, footer: str, tokens: int, is_final: bool) -> hikari.Embed:
    """Builds a standardized AI response embed."""
    display = text if len(text) <= 4000 else text[:4000]
    color = 0x57F287 if is_final else 0x3498DB
    footer_text = f"{footer} | {tokens} tokens" if tokens else footer
    return hikari.Embed(description=display or "…", color=color).set_footer(footer_text)


def build_source_components(sources: set[tuple[str, str]], max_items: int = 20) -> list[hikari.api.MessageActionRowBuilder]:
    """Build Discord ActionRow components from source (title, url) pairs."""
    rows: list[hikari.api.MessageActionRowBuilder] = []
    for idx, (title, url) in enumerate(list(sources)[:max_items]):
        if idx % 5 == 0:
            row = hikari.impl.MessageActionRowBuilder()
            rows.append(row)
        row.add_component(hikari.impl.LinkButtonBuilder(label=title[:80], url=url))
    return rows
