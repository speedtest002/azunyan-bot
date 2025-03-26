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
        'deepseek/deepseek-r1',
        'google/gemini-2.0-flash-lite-preview-02-05',
        'google/gemini-2.5-pro-exp-03-25',
        'qwen/qwen2.5-vl-32b-instruct'
    ]
    async def model_autocomplete(
        self,
        interaction: Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=model, value=model)
            for model in AIChatCommand.models if current.lower() in model.lower()
        ]
    @app_commands.autocomplete(model=model_autocomplete)
    @app_commands.command(name="ai_setting", description="Lựa chọn mô hình và thêm api key.")
    @app_commands.describe(
        model='Mô hình, có thể tìm thêm từ https://openrouter.ai/models?q=%28free%29',
        api_key='Cách lấy: Tạo tài khoản ở https://openrouter.ai/ -> Keys -> Create Key.'
    )
    @app_commands.dm_only()
    async def ai_setting(self, interaction: Interaction, model: str, api_key: str = None):
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
        first_embed.set_footer(text=f"{model}")
        response_message = await ctx.send(embed=first_embed)  # tin nhắn ban đầu
        await asyncio.sleep(1)
        #xu ly prompt
        prompt = self.parse_prompt(prompt)
        try:
            response_stream = self.to_the_moon(api_key=api_key, model=model, message=prompt)
            await self.update_embed(response_message, response_stream, model)
            return
        except Exception as e:
            print(e)
            await response_message.edit(embed=Embed(description=f"{e}\n¯\_(ツ)_/¯\nHãy kiểm tra lại model/api key", color=Color.red()))
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