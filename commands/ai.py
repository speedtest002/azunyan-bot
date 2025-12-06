from discord.ext import commands
from discord import app_commands, Embed, Message, Color
import asyncio
import re
import os
import httpx
import json
from urllib.parse import urlparse


class GeminiAICommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("no GEMINI_API_KEY")
        
        self.worker_url = os.getenv('CLOUDFLARE_WORKER_URL')
        if not self.worker_url:
            raise ValueError("no CLOUDFLARE_WORKER_URL")
        if not self.worker_url.startswith(('http://', 'https://')):
            raise ValueError("invalid CLOUDFLARE_WORKER_URL")
        
        self.models = [
            'gemini-2.5-pro',
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',
            'gemini-2.0-flash'
        ]

    @commands.hybrid_command(name="ai")
    @app_commands.describe(prompt='prompt')
    async def ai(self, ctx: commands.Context, *, prompt: str):
        embed = Embed(description="Thinking...", color=Color.purple())
        response_message = await ctx.send(embed=embed)
        
        try:
            image_urls = await self.collect_image_urls(ctx, prompt)
            response_text, total_tokens, model_used = await self.call_gemini(prompt, image_urls)
            await self.stream_response(response_message, response_text, total_tokens, model_used)
        except Exception as error:
            await response_message.edit(embed=Embed(description=f"Error: {error}", color=Color.red()))
            print(f"ai error: {error}")
    
    async def collect_image_urls(self, ctx: commands.Context, prompt: str) -> list:
        image_urls = []
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in image_extensions):
                    image_urls.append(attachment.url)
        
        if ctx.message.reference:
            try:
                replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                for attachment in replied_message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in image_extensions):
                        image_urls.append(attachment.url)
                for embed in replied_message.embeds:
                    if embed.image:
                        image_urls.append(embed.image.url)
                    if embed.thumbnail:
                        image_urls.append(embed.thumbnail.url)
            except:
                pass
        
        detected_url = self.detect_image_url(prompt)
        if detected_url:
            image_urls.append(detected_url)
        
        return image_urls
    
    async def call_gemini(self, prompt: str, image_urls: list):
        last_error = None
        
        for model in self.models:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(self.worker_url, json={
                        "prompt": prompt,
                        "imageUrls": image_urls or [],
                        "apiKey": self.api_key,
                        "model": model
                    })
                
                if response.status_code != 200:
                    if response.status_code == 429 or '429' in response.text or 'quota' in response.text.lower():
                        continue
                    raise Exception(f"worker: {response.status_code}")
                
                response_text, total_tokens = self.parse_response(response.text)
                return response_text, total_tokens, model
                
            except Exception as error:
                last_error = error
                error_str = str(error).lower()
                if '429' in error_str or '503' in error_str or 'quota' in error_str:
                    continue
                raise error
        
        raise Exception(f"all models failed: {last_error}")
    
    def parse_response(self, response_text: str) -> tuple:
        content_parts = []
        total_tokens = 0
        
        try:
            data = json.loads(response_text)
            items = data if isinstance(data, list) else [data]
            
            for item in items:
                for candidate in item.get('candidates', []):
                    for part in candidate.get('content', {}).get('parts', []):
                        if not part.get('thought') and 'text' in part:
                            content_parts.append(part.get('text', ''))
                
                usage_metadata = item.get('usageMetadata', {})
                if usage_metadata.get('totalTokenCount'):
                    total_tokens = usage_metadata.get('totalTokenCount')
        except:
            content_parts.append(response_text)
        
        return ''.join(content_parts), total_tokens
    
    def detect_image_url(self, text: str):
        for word in text.split():
            path = urlparse(word).path
            if re.search(r'\.(jpg|jpeg|png|gif|webp)$', path, re.IGNORECASE):
                return word
        return None
    
    async def stream_response(self, message: Message, text: str, tokens: int, model: str):
        max_length = 4000
        
        if len(text) > max_length:
            await self.send_long_response(message, text, tokens, model)
            return
        
        embed = Embed(description="", color=Color.blue())
        footer_text = f"{model} | token: {tokens}" if tokens else model
        embed.set_footer(text=footer_text)
        
        chunk_size = 50
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        update_counter = 0
        
        for chunk in chunks:
            embed.description += chunk
            update_counter += 1
            
            if update_counter >= 4:
                await message.edit(embed=embed)
                update_counter = 0
                await asyncio.sleep(0.3)
        
        embed.color = Color.green()
        await message.edit(embed=embed)
    
    async def send_long_response(self, message: Message, text: str, tokens: int, model: str):
        max_length = 4000
        parts = []
        current_part = ""
        
        for line in text.split('\n'):
            if len(current_part) + len(line) + 1 > max_length:
                if current_part:
                    parts.append(current_part)
                    current_part = line
                else:
                    parts.append(line[:max_length])
                    current_part = line[max_length:]
            else:
                current_part = current_part + '\n' + line if current_part else line
        
        if current_part:
            parts.append(current_part)
        
        footer_text = f"{model} | token: {tokens}" if tokens else model
        total_parts = len(parts)
        
        first_embed = Embed(description=parts[0], color=Color.green())
        first_embed.set_footer(text=f"{footer_text} (1/{total_parts})")
        await message.edit(embed=first_embed)
        
        for index, part in enumerate(parts[1:], start=2):
            embed = Embed(description=part, color=Color.green())
            embed.set_footer(text=f"{footer_text} ({index}/{total_parts})")
            await message.channel.send(embed=embed)
            await asyncio.sleep(0.5)


async def setup(bot):
    await bot.add_cog(GeminiAICommand(bot))