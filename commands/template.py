from discord import *
from discord.ext import commands
#import ...

class TemplateCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #if you want to make hybrid command, use:
    @commands.hybrid_command(name="command_name")
    async def command_name(ctx, parameter_1: str, parameter_2: int):
        """
        Decription of the command

        Parameters:
        ----------
        parameter_1: str
            Decrption of parameter 1
        parameter_2: int
            Decrption of parameter 2
        """
        #add your code here

        # if you want bot send a message
        await ctx.send("add message here")
    # for anything else, please read the docmentation of discord.py
    # https://discordpy.readthedocs.io/en/stable/
    # or you can ask me for help

async def setup(bot):
    await bot.add_cog(TemplateCommand(bot))