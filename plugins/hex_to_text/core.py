def decode_hex(content: str) -> str:
    return bytes.fromhex(content).decode("utf-8")