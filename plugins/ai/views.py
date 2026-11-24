"""plugins/ai/views.py — UI components and embed builders for AI plugin"""
from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

import hikari
import miru

MAX_EMBED_LEN = 4000
MAX_LINK_URL_LEN = 512
MAX_BUTTON_LABEL_LEN = 80
MAX_SOURCE_BUTTONS = 20

_STRUCTURAL_MARKERS = ("\n### ", "\n## ", "\n# ", "\n- ", "\n* ", "\n> ")
_SENTENCE_ENDINGS = (". ", "? ", "! ")


def sanitize_sources(
    sources: Iterable[tuple[str | None, str | None]],
    max_items: int = MAX_SOURCE_BUTTONS,
) -> list[tuple[str, str]]:
    """Validate, deduplicate, and clamp (title, url) pairs for Discord LinkButtons."""
    cleaned: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for raw_title, raw_url in sources:
        if len(cleaned) >= max_items:
            break
        if not isinstance(raw_url, str):
            continue
        url = raw_url.strip()
        if not url or len(url) > MAX_LINK_URL_LEN or url in seen_urls:
            continue

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue

        title = (raw_title or "").strip() if isinstance(raw_title, str) else ""
        label = (title or parsed.netloc or "Source")[:MAX_BUTTON_LABEL_LEN]
        if not label:
            label = "Source"

        seen_urls.add(url)
        cleaned.append((label, url))

    return cleaned


def smart_truncate(text: str, max_len: int = MAX_EMBED_LEN) -> str:
    """Truncate text at a natural boundary near max_len to avoid breaking Markdown.

    Priority: \\n\\n > heading/bullet/quote markers > \\n > sentence endings > space > hard cut
    """
    if len(text) <= max_len:
        return text

    chunk = text[:max_len]
    min_pos = int(max_len * 0.3)

    pos = chunk.rfind("\n\n")
    if pos > min_pos:
        return chunk[:pos]

    best_marker_pos = max((chunk.rfind(pat) for pat in _STRUCTURAL_MARKERS), default=-1)
    if best_marker_pos > min_pos:
        return chunk[:best_marker_pos]

    pos = chunk.rfind("\n")
    if pos > min_pos:
        return chunk[:pos]

    best_sentence_pos = max((chunk.rfind(pat) for pat in _SENTENCE_ENDINGS), default=-1)
    if best_sentence_pos > min_pos:
        return chunk[: best_sentence_pos + 1]

    pos = chunk.rfind(" ")
    if pos > min_pos:
        return chunk[:pos]

    return chunk


def _find_open_code_fence(text: str) -> str | None:
    """Return the opening fenced code block header (e.g. '```python') if unclosed."""
    open_fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            if open_fence is None:
                # Giữ lại ngôn ngữ sau ``` nhưng giới hạn độ dài để không làm tràn page sau
                token = stripped.split()[0] if stripped.split() else "```"
                open_fence = token[:32]
            else:
                open_fence = None
    return open_fence


def split_text(text: str, max_len: int = MAX_EMBED_LEN) -> list[str]:
    """Split text into Discord-safe chunks while keeping fenced code blocks balanced."""
    if not text:
        return []
    if len(text) <= max_len:
        return [text]

    parts: list[str] = []
    remaining = text
    # Chừa sẵn chỗ để đóng "\n```" nếu chunk kết thúc giữa chừng trong code block
    effective_max = max(max_len - 8, 100)

    while len(remaining) > max_len:
        chunk = smart_truncate(remaining, effective_max)
        if not chunk:
            chunk = remaining[:effective_max]

        rest = remaining[len(chunk) :].lstrip("\n")
        open_fence = _find_open_code_fence(chunk)
        if open_fence is not None and rest:
            chunk = f"{chunk}\n```"
            # Chỉ mở lại fence ở trang kế tiếp nếu còn nội dung thực sự sau fence
            rest = f"{open_fence}\n{rest}"

        parts.append(chunk)
        if len(rest) >= len(remaining):
            # Phòng vệ chống vòng lặp vô hạn với input bất thường
            parts.append(rest[:max_len])
            rest = rest[max_len:]
        remaining = rest

    if remaining:
        parts.append(remaining)
    return parts


class AIPaginationView(miru.View):
    def __init__(
        self,
        pages: list[str],
        model_name: str,
        tokens: int,
        sources: Iterable[tuple[str | None, str | None]],
        author_id: int,
    ) -> None:
        super().__init__(timeout=3600)
        self.pages = pages or ["…"]
        self.model_name = model_name
        self.tokens = tokens
        self.author_id = author_id
        self.current_page = 1
        self.total_pages = len(self.pages)

        clean_sources = sanitize_sources(sources, max_items=MAX_SOURCE_BUTTONS)
        for i, (label, url) in enumerate(clean_sources):
            self.add_item(miru.LinkButton(label=label, url=url, row=1 + (i // 5)))

        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev.disabled = self.current_page <= 1
        self.next.disabled = self.current_page >= self.total_pages
        self.page_indicator.label = f"{self.current_page}/{self.total_pages}"

    def _build_embed(self) -> hikari.Embed:
        page_text = self.pages[self.current_page - 1]
        display = smart_truncate(page_text, MAX_EMBED_LEN)
        embed = hikari.Embed(description=display or "…", color=0x57F287)
        base_footer = f"{self.model_name} | {self.tokens} tokens" if self.tokens else self.model_name
        embed.set_footer(f"{base_footer} ({self.current_page}/{self.total_pages})")
        return embed

    @miru.button(emoji="◀️", style=hikari.ButtonStyle.PRIMARY, row=0)
    async def prev(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        if ctx.user.id != self.author_id:
            await ctx.respond("Bạn không có quyền sử dụng nút này.", flags=hikari.MessageFlag.EPHEMERAL)
            return
        if self.current_page > 1:
            self.current_page -= 1
            self._update_buttons()
        await ctx.edit_response(embed=self._build_embed(), components=self)

    @miru.button(label="1/1", style=hikari.ButtonStyle.SECONDARY, disabled=True, row=0)
    async def page_indicator(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        pass

    @miru.button(emoji="▶️", style=hikari.ButtonStyle.SUCCESS, row=0)
    async def next(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        if ctx.user.id != self.author_id:
            await ctx.respond("Bạn không có quyền sử dụng nút này.", flags=hikari.MessageFlag.EPHEMERAL)
            return
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._update_buttons()
        await ctx.edit_response(embed=self._build_embed(), components=self)

    async def on_timeout(self) -> None:
        self.prev.disabled = True
        self.next.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(components=self)
            except Exception:
                pass


def build_ai_embed(text: str, footer: str, tokens: int, is_final: bool) -> hikari.Embed:
    """Build a standardized AI response embed."""
    if not is_final and len(text) > MAX_EMBED_LEN:
        # Khi đang stream vượt quá 4000 ký tự, hiện phần đuôi mới nhất để user thấy tiến độ
        display = "…\n" + text[-(MAX_EMBED_LEN - 2) :]
    else:
        display = smart_truncate(text, MAX_EMBED_LEN)

    color = 0x57F287 if is_final else 0x3498DB
    footer_text = f"{footer} | {tokens} tokens" if tokens else footer
    return hikari.Embed(description=display or "…", color=color).set_footer(footer_text)


def build_source_components(
    sources: Iterable[tuple[str | None, str | None]],
    max_items: int = MAX_SOURCE_BUTTONS,
) -> list[hikari.api.MessageActionRowBuilder]:
    """Build Discord ActionRow components from sanitized (title, url) pairs."""
    clean_sources = sanitize_sources(sources, max_items=max_items)
    rows: list[hikari.api.MessageActionRowBuilder] = []
    for idx, (label, url) in enumerate(clean_sources):
        if idx % 5 == 0:
            row = hikari.impl.MessageActionRowBuilder()
            rows.append(row)
        row.add_component(hikari.impl.LinkButtonBuilder(label=label, url=url))
    return rows
