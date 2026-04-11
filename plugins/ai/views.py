"""plugins/ai/views.py — UI components and embed builders for AI plugin"""
import hikari

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


def build_ai_embed(text: str, footer: str, tokens: int, is_final: bool, sources: set[str] | None = None) -> hikari.Embed:
    """Builds a standardized AI response embed."""
    if sources:
        text += "\n\n**Source:**\n" + "\n".join(f"- {s}" for s in sources)
    
    # Discord embed description limit is 4096, we use 4000 for safety
    display = text if len(text) <= 4000 else text[-4000:]
    color = 0x57F287 if is_final else 0x3498DB
    footer_text = f"{footer} | {tokens} tokens" if tokens else footer
    
    return hikari.Embed(description=display or "…", color=color).set_footer(footer_text)
