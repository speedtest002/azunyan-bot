import discord
from discord.ext import commands

class Hex2TextCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(Hex2TextCommand(bot))

@discord.app_commands.context_menu(name="Hex to text")
async def hex_to_text(interaction: discord.Interaction, message: discord.Message):
    """
    Convert hex to text
    """
    try:
        decoded_text = bytes.fromhex(message.content).decode('utf-8')
        await interaction.response.send_message(f"Text: {decoded_text}")
    except Exception as e:
        await interaction.response.send_message(f"Co chac day la hex khong ?", ephemeral=True)

async def setup(bot):
    bot.tree.add_command(hex_to_text)
    await bot.add_cog(Hex2TextCommand(bot))