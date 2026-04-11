def parse_kanji(raw: dict) -> dict | str:
    if raw.get("status") != 200 or not raw.get("results"):
        return "Không tìm thấy kanji."

    item = raw["results"][0]
    description_lines: list[str] = []
    fields: list[dict] = []

    level = item.get("level")
    if isinstance(level, list) and level:
        description_lines.append(f"JLPT: {level[0]}")

    stroke_count = item.get("stroke_count")
    if isinstance(stroke_count, str) and stroke_count.strip():
        description_lines.append(f"Số nét: {stroke_count.strip()}")

    for name, key, inline in (
        ("Kunyomi", "kun", True),
        ("Onyomi", "on", True),
        ("Hán Việt", "mean", True),
    ):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            fields.append({"name": name, "value": value.strip(), "inline": inline})

    detail = item.get("detail")
    if isinstance(detail, str) and detail.strip():
        meaning_lines = [part.strip() for part in detail.split("##") if part.strip()]
        if meaning_lines:
            fields.append({"name": "Nghĩa", "value": "\n".join(meaning_lines), "inline": False})

    freq = item.get("freq")
    if freq:
        fields.append({"name": "Phổ biến thứ", "value": str(freq), "inline": False})

    examples = item.get("examples")
    if isinstance(examples, list):
        example_lines: list[str] = []
        for example in examples:
            if not isinstance(example, dict):
                continue

            word = example.get("w")
            reading = example.get("p")
            meaning = example.get("m")
            if not all(isinstance(part, str) and part.strip() for part in (word, reading, meaning)):
                continue

            line = f"{word.strip()} ({reading}): {meaning.strip()}"
            han_viet = example.get("h")
            if isinstance(han_viet, str) and han_viet.strip():
                line += f" ({han_viet.strip()})"
            example_lines.append(line)

        if example_lines:
            fields.append({"name": "Ví dụ", "value": "\n".join(example_lines), "inline": False})

    payload = {
        "title": f"Kanji: {item.get('kanji', '?')}",
        "color": 0x3489EB,
        "fields": fields,
    }
    if description_lines:
        payload["description"] = "\n".join(description_lines)
    return payload
