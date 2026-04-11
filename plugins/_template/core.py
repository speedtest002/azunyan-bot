"""
plugins/_template/core.py — Chứa toàn bộ logic nghiệp vụ (Business Logic).

Mọi tính toán, gọi API, tương tác DB hoặc xử lý chuỗi phải đặt ở đây.
Tuyệt đối KHÔNG import `arc.GatewayContext` hay `lightbulb.PrefixContext` vào file này.
"""

def process_example_logic(text: str, number: int | None) -> str:
    """Hàm xử lý logic ví dụ."""
    if number is not None:
        return f"Bạn đã nhập văn bản: `{text}` và số: `{number}`. Logic đã xử lý thành công!"
    return f"Bạn đã nhập văn bản: `{text}`. Không có số nào được cung cấp."