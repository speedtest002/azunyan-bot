import os
from discord.ext import commands
from aiohttp import ClientSession

async def load_extensions(bot):
    for filename in os.listdir('./commands'):
        if filename.endswith('.py') and filename != '__init__.py' and filename != 'template.py':
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
        await load_extensions(self)

    async def on_ready(self) -> None:
        print(f'Logged in as {self.user}')
        await self.tree.sync()