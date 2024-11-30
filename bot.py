import os
import asyncio
import logging
import logging.handlers
import discord
from aiohttp import ClientSession
import uvicorn
from dotenv import load_dotenv
from feature import *
from pymongo import MongoClient

load_dotenv()

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
                command_prefix=(os.getenv('PREFIX'), os.getenv('PREFIX').capitalize()),
                web_client=our_client,
                initial_extensions=[],
                intents=intents,
                case_insensitive=True,
        ) as bot:
            asyncio.create_task(uvicorn.Server(uvicorn.Config(SendMessage(bot).app, host=str(os.getenv("HOST")), port=int(os.getenv("PORT")), log_level="info")).serve())
            await bot.start(str(os.getenv('DISCORD_TOKEN')))

asyncio.run(main())