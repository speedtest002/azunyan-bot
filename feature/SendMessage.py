import os
from fastapi import FastAPI, Query
import discord
from discord.ext import commands
from typing import Optional

class SendMessage:
    def __init__(self, bot: commands.Bot):
        self.app = FastAPI()
        self.app.post("/send_message")(self.send_message)
        self.bot = bot

    async def send_message(self, message: Optional[str] = Query(None)):
        if message is None:
            return {"error": "Message is required"}
        await self.send_message_to_channel(message)
        return {"status": "Message sent to Discord."}

    async def send_message_to_channel(self, message):
        channel = self.bot.get_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
        if channel and channel.type == discord.ChannelType.news:
            msg = await channel.send(message)
            await msg.publish()
        elif channel:
            await channel.send(message)
        else:
            print("Channel not found")