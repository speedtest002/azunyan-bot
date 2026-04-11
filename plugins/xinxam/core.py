import json
import logging
import random
from pathlib import Path
import hikari
import pytz
import vnlunar
from datetime import datetime

RENTRY_URL = "https://rentry.co/dientich100quexam"
DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "100quexam.json"
_fortune_map: dict = {}

def _load_data() -> None:
    try:
        with DATA_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            _fortune_map.update({str(item["ID"]): item for item in data})
    except Exception as e:
        log.error(f"Lỗi load data xăm: {e}")

_load_data()

def _get_lunar_year() -> str:
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    now = datetime.now(tz)
    lunar_info = vnlunar.get_full_info(now.day, now.month, now.year)
    return lunar_info["can_chi"]["year"]

def build_xinxam_embed(author_id: int, author_name: str, avatar_url: str) -> hikari.Embed:
    lunar_year = _get_lunar_year()
    rng = random.Random(f"{author_id}-{lunar_year}")
    lucky_number = str(rng.randint(1, 100))
    item = _fortune_map.get(lucky_number, _fortune_map.get("1", {}))

    rank = item.get("Rank", "").upper()
    if "THƯỢNG" in rank:
        color = hikari.Color(0xFF0000)
    elif "HẠ" in rank:
        color = hikari.Color(0x010101)
    else:
        color = hikari.Color(0xFFD700)

    embed = hikari.Embed(
        title=f"⛩️ LÁ XĂM SỐ {item.get('ID', '?')}: {item.get('Rank', '')}",
        color=color,
    )
    embed.add_field("📜 Quẻ Thơ", f"```fix\n{item.get('Original', '')}\n```", inline=False)
    embed.add_field("🔤 Phiên Âm", f"*{item.get('Transliteration', '')}*", inline=False)
    embed.add_field("📝 Dịch Thơ", f"*{item.get('Translation', '')}*", inline=False)
    embed.add_field("💡 Lời Bàn", f"┕ {item.get('Comment', '')}", inline=False)
    embed.add_field("🔮 Điềm Quẻ", f"┕ {item.get('Divination', '')}", inline=False)

    ref_title = item.get("reference_translated", item.get("Reference", "Tích cổ"))
    ref_detail = item.get("reference_detail", item.get("ReferenceDetail", ""))
    if len(ref_detail) > 950:
        ref_value = f"> Nội dung tích cổ này rất dài.\n> 🔗 **[Xem toàn bộ điển tích]({RENTRY_URL})**"
    else:
        ref_value = f">>> {ref_detail}" if ref_detail else "Chưa có thông tin."
    embed.add_field(f"📖 Tích Cổ: {ref_title}", ref_value, inline=False)

    explanation = item.get("Explanation", "")
    exp_value = (
        f"👉 Nội dung quá dài, xem chi tiết tại: {RENTRY_URL}"
        if len(explanation) > 950
        else f"```yaml\n{explanation}\n```"
    )
    embed.add_field("🔍 Giải", exp_value, inline=False)
    embed.set_footer(text=f"Người xin: {author_name} • Năm {lunar_year}", icon=avatar_url)
    embed.timestamp = datetime.now(pytz.utc)
    return embed