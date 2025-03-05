from discord.ext import commands
from discord import app_commands
from discord import Interaction, Embed, Message, Color
from feature import MongoManager
from typing import List
import asyncio
from openai import OpenAI
import re
from urllib.parse import urlparse

class AIChatCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.AIChat_api_key_collection = MongoManager.get_collection('AIChat_api_keys')
        
    models =[
        app_commands.Choice(name='Nên chọn cái nào?', value="help"),
        app_commands.Choice(name='deepseek-r1', value='deepseek/deepseek-r1'),
        app_commands.Choice(name='deepseek-chat', value='deepseek/deepseek-chat'),
        app_commands.Choice(name='deepseek-r1-distill-llama-70b', value='deepseek/deepseek-r1-distill-llama-70b'),
        app_commands.Choice(name='google-gemini-2.0-flash-thinking-exp', value='google/gemini-2.0-flash-thinking-exp'),
        app_commands.Choice(name='google-gemini-2.0-flash-lite-preview-02-05', value='google/gemini-2.0-flash-lite-preview-02-05'),
        app_commands.Choice(name='qwen-vl-plus', value='qwen/qwen-vl-plus')
    ] 
    @app_commands.command(name="ai_setting", description="Lựa chọn mô hình và thêm api key.")
    @app_commands.choices(model=models)
    @app_commands.describe(
        model='Mô hình',
        api_key='Cách lấy: Tạo tài khoản ở https://openrouter.ai/ -> Keys -> Create Key.'
    )
    @app_commands.dm_only()
    async def ai_setting(self, interaction: Interaction, model: str, api_key: str = None):
        if model == "help":
            response = [
                '`deepseek-r1` - Mô hình tàu khựa, rất chậm',
                '`deepseek-chat` - Cũng mô hình tàu tàu khựa nhưng ngu hơn, rất chậm',
                '`deepseek-r1-distill-llama-70b` - Cũng mô hình tàu tàu khựa nhưng nhanh hơn và ngu hơn',
                '`google-gemini-2.0-flash-thinking-exp` - Mô hình của bố Mẽo, nhanh, biết suy nghĩ và hỗ trợ đọc link hình ảnh',
                '`google-gemini-2.0-flash-lite-preview-02-05` - Cũng là mô hình của bố Mẽo, nhanh nhưng không đọc link hình ảnh',
                '`qwen-vl-plus` - Của bố khựa, chỉ nên dùng để đọc hình ảnh'
            ]
            await interaction.response.send_message('\n'.join(response))
            return
        user_id = interaction.user.id
        self.AIChat_api_key_collection.update_one({'_id': user_id}, {'$set': {'model': model}}, upsert=True)
        if api_key is None: # chi thay doi model
            await interaction.response.send_message(f'Bạn đã đổi model thành công!')
            return
        self.AIChat_api_key_collection.update_one({'_id': user_id}, {'$set': {'api_key': api_key}}, upsert=True)
        await interaction.response.send_message(f'Bạn đã thêm api key thành công! \nLưu ý, chỉ dùng api key từ tài khoản mới và không thêm bất cứ hình thức thanh toán nào.')
        
    @commands.hybrid_command(name="ai")
    @app_commands.describe(prompt='Nội dung.')
    async def ai(self, ctx: commands.Context, *, prompt: str):
        """Gọi nô lệ"""
        user_id = ctx.author.id
        
        user_data = self.AIChat_api_key_collection.find_one({'_id': user_id})
        api_key = user_data.get('api_key') if user_data else None
        if api_key is None:
            await ctx.send('Bạn chưa cung cấp api key. Hãy thêm api key bằng cách dùng lệnh `/ai_setting` trong dm với bot.', ephemeral=True)
            return
        model = user_data.get('model') if user_data else None
        if model is None:
            await ctx.send('Bạn chưa chọn model. Hãy chọn model bằng cách dùng lệnh `/ai_setting` trong dm với bot.', ephemeral=True)
            return
        
        first_embed = Embed(description="\u200b",color=Color.purple())
        response_message = await ctx.send(embed=first_embed)  # tin nhắn ban đầu
        await asyncio.sleep(2)
        #xu ly prompt
        prompt = self.parse_prompt(prompt)
        try:
            response_stream = self.to_the_moon(api_key=api_key, model=model, message=prompt)
            await self.update_embed(response_message, response_stream, model=model)
            return
        except Exception as e:
            print(e)
            await response_message.edit(content=f'{e}')
            return

    def parse_prompt(self, prompt: str):
        content = [{"type": "text", "text": prompt}]
        
        if (link := self.link_image_detect(prompt)) is not None:
            content.append({"type": "image_url", "image_url": {"url": link}})
        
        return [{"role": "user", "content": content}]

    async def to_the_moon(self, api_key: str, model: str, message: list):
        client = OpenAI(
        base_url='https://openrouter.ai/api/v1',
        api_key=f'{api_key}',
        )
        completion = client.chat.completions.create(
            model=f'{model}:free',
            stream=True,
            max_tokens=4096, # limit of Discord api is 4000 characters in embed
            messages=message
        )

        for chunk in completion:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
                
    async def update_embed(self, message: Message, response_stream, model: str):
        embed = Embed(description="", color=Color.blue(), )
        embed.set_footer(text=model)
        async for chunk in response_stream:
            embed.description += chunk  # Thêm dữ liệu mới vào Embed
            await asyncio.sleep(0.5)
            await message.edit(embed=embed)  # Cập nhật Embed
        embed.color=Color.green()
        await message.edit(embed=embed)  # Cập nhật lần cuối
                    
    def link_image_detect(self, message: str):
        for word in message.split():
            url_path = urlparse(word).path  
            if re.search(r'\.(jpg|jpeg|png)$', url_path, re.IGNORECASE):
                return word
        return None
    
async def setup(bot):
    await bot.add_cog(AIChatCommand(bot))