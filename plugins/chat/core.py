async def send_chat_message(channel, content: str) -> None:
    await channel.send(content)