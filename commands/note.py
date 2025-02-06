from discord.ext import commands
from discord import *
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
import re 
import os
load_dotenv()

uri = os.getenv("MONGO_URI")
client = MongoClient(uri)

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
db = client["azunyan"]
collection = db["azunote"]

def save_text(key, text):
    collection.insert_one({"key":key, "text":text})

def get_text(key):
    return collection.find_one({"key":key})["text"]

class NoteCommand(commands.Cog, name = "note"):
    def __init__(self, bot):
        self.bot = bot

    '''
    azunote <key>: <text> 
    '''

    @commands.command(name="note")
    async def note(self, ctx):       
        message = ctx.message.content.split("azunote ", 1)[1] 
        parts = re.split(r": |\:\n", message, maxsplit=1)
        key = parts[0]

        if len(parts) <= 1:
            await ctx.send(get_text(key))    
        else:
            if collection.find_one({"key": key}):
                await ctx.send("Key này đã tồn tại, hãy chọn key khác nhé!")
            else:    
                text = parts[1]
                save_text(key, text)
                await ctx.send("Azu-nyan đã lưu note!!")

async def setup(bot):
    await bot.add_cog(NoteCommand(bot))