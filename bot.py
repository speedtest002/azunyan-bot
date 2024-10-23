import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import asyncio
#from pymongo import MongoClient

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=("soda", "Soda"), intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

async def load_extensions():
    for filename in os.listdir('./commands'):
        if filename.endswith('.py') and filename != '__init__.py':
            await bot.load_extension(f'commands.{filename[:-3]}')

# Hàm chính để chạy bot
async def main():
    load_dotenv()
    async with bot:
        await load_extensions()
        await bot.start(os.getenv('TOKEN'))
        
asyncio.run(main())