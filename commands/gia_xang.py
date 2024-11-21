from typing import Optional
import discord
from discord.ext import commands
from discord import Intents
from fastapi import FastAPI, Query
import uvicorn
import asyncio
import os
from dotenv import load_dotenv

class GiaXangCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    app = FastAPI()
    load_dotenv()

    DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

    async def send_message_to_channel(self, channel_id, message):
        channel = self.bot.get_channel(channel_id)  # Sử dụng self.bot thay vì commands.get_channel
        if channel.type == discord.ChannelType.news:
            msg = await channel.send(message)
            await msg.publish()
        elif channel is not None:
            await channel.send(message)
        else:
            print("Channel not found")

    @app.post("/send_message")
    async def send_message(
        self,
        message: Optional[str] = Query(None)
    ):
        if message is None:
            return {"error": "Message is required"}

        await self.send_message_to_channel(self.DISCORD_CHANNEL_ID, message)
        return {"status": "Message sent to Discord."}

    async def setup_hook(self):
        config = uvicorn.Config(self.app, host=os.getenv("HOST"), port=int(os.getenv("PORT")), log_level="info")
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())

async def setup(bot):
    await bot.add_cog(GiaXangCommand(bot))