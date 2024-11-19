import ast
import os
import asyncio
import logging
import logging.handlers
import discord
from discord.ext import commands
from aiohttp import ClientSession
from fastapi import FastAPI, Query
import uvicorn
from typing import Optional

app = FastAPI()

async def load_extensions(bot):
    for filename in os.listdir('./commands'):
        if filename.endswith('.py') and filename != '__init__.py':
            extension = f'commands.{filename[:-3]}'
            try:
                await bot.load_extension(extension)
                print(f'Loaded extension: {extension}')
            except Exception as e:
                print(f'Failed to load extension {extension}: {e}')

class CustomBot(commands.Bot):
    def __init__(
        self,
        *args,
        web_client: ClientSession,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.web_client = web_client

    async def setup_hook(self) -> None:
        config = uvicorn.Config(app, host=os.getenv("HOST"), port=int(os.getenv("PORT")), log_level="info")
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())
        print("FastAPI server started!")
        #await load_extensions(self)

    async def on_ready(self) -> None:
        print(f'Logged in as {self.user}')
        await self.tree.sync()

async def main():
    #Logging
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=64 * 1024 * 1024,  # 64 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #Run bot
    async with ClientSession() as our_client:
        intents = discord.Intents.default()
        intents.message_content = True
        async with CustomBot(
                command_prefix=os.getenv('PREFIX'),
                web_client=our_client,
                initial_extensions=[],
                intents=intents,
                case_insensitive=True,
        ) as bot:
            await load_extensions(bot)
            await bot.start(os.getenv('TOKEN'))

        @app.post("/send_message")
        async def send_message(message: Optional[str] = Query(None)):
            if message is None:
                return {"error": "Message is required"}
            await send_message_to_channel(message)
            return {"status": "Message sent to Discord."}
        async def send_message_to_channel(message):
            channel = bot.get_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
            if channel.type == discord.ChannelType.news:
                msg = await channel.send(message)
                await msg.publish()
            elif channel is not None:
                await channel.send(message)
            else:
                print("Channel not found")
asyncio.run(main())