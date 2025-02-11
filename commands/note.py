from discord.ext import commands
from discord import *
from feature import MongoManager
import re 


class NoteCommand(commands.Cog, name = "note"):
    def __init__(self, bot):
        self.bot = bot
        self.note_collection = MongoManager.get_collection("note")
    '''
    azunote <key>: <text> 
    '''
    def save_text(self, key, text):
        self.note_collection.insert_one({"key":key, "text":text})

    def get_text(self, key):
        return self.note_collection.find_one({"key":key})["text"]
    
    @commands.command(name="note")
    async def note(self, ctx, *message):
        
        message = ' '.join(message)
        #ctx.message.content.split("azunote ", 1)[1]
        parts = re.split(r": |\:\n", message, maxsplit=1)
        key = parts[0]

        if len(parts) <= 1:
            await ctx.send(self.get_text(key))    
        else:
            if self.note_collection.find_one({"key": key}):
                await ctx.send("Key này đã tồn tại, hãy chọn key khác nhé!")
            else:    
                text = parts[1]
                self.save_text(key, text)
                await ctx.send("Azu-nyan đã lưu note!!")

async def setup(bot):
    await bot.add_cog(NoteCommand(bot))