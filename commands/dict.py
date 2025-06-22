import discord
from discord.ext import commands
import requests

class TemplateCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dictionary", aliases=["dict","d"])
    async def dictionary(self, ctx, word: str):
        """
        Tra từ vựng bằng dictionaryapi.dev

        Parameters:
        ----------
        word: str
            Từ cần tra nghĩa
        """
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            meanings = []
            for meaning in data[0].get('meanings', []):
                part_of_speech = meaning.get('partOfSpeech', '')
                for definition in meaning.get('definitions', []):
                    meanings.append(f"- ({part_of_speech}): {definition['definition']}")
            
            meanings_text = "\n".join(meanings) if meanings else "Word not found."

            embed = discord.Embed(
                title=f"'{word}':",
                color=0x00ff00
            )
            embed.add_field(name="Meanings:", value=meanings_text, inline=False)
            await ctx.send(embed=embed)

        else:
            await ctx.send("Word not found or an error occurred.")

async def setup(bot):
    await bot.add_cog(TemplateCommand(bot))
