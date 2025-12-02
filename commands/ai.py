from discord.ext import commands
from discord import app_commands
from discord import Interaction, Embed, Message, Color
import asyncio
import re
from urllib.parse import urlparse
import os
import httpx
from google import genai
from google.genai import types


class GeminiAICommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Lấy API key từ biến môi trường
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY không tồn tại trong .env")

        # Lấy Cloudflare Worker URL
        self.worker_url = os.getenv('CLOUDFLARE_WORKER_URL')
        if not self.worker_url:
            raise ValueError("CLOUDFLARE_WORKER_URL không tồn tại trong .env")
        
        # Validate worker URL has protocol
        if not self.worker_url.startswith(('http://', 'https://')):
            raise ValueError("CLOUDFLARE_WORKER_URL phải bắt đầu với http:// hoặc https://")
        
        # Khởi tạo client Gemini
        self.client = genai.Client(api_key=self.api_key)
        
        # Danh sách models ưu tiên (fallback chain)
        self.models = [
            'gemini-2.5-pro',
            'gemini-2.5-flash', 
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',
            'gemini-2.0-flash',
        ]

    @commands.hybrid_command(name="ai")
    @app_commands.describe(prompt='prompt')
    async def ai(self, ctx: commands.Context, *, prompt: str):
        """gọi nô lệ gemini"""
            
        # Tạo embed ban đầu
        initial_embed = Embed(
            description="⏳ Đang xử lý...",
            color=Color.purple()
        )
        response_message = await ctx.send(embed=initial_embed)
        
        try:
            # Thu thập tất cả hình ảnh từ mọi nguồn
            image_urls = []
            
            # 1. Hình ảnh từ attachments (người dùng upload)
            if ctx.message.attachments:
                for attachment in ctx.message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        image_urls.append(attachment.url)
            
            # 2. Hình ảnh từ tin nhắn được reply
            if ctx.message.reference:
                try:
                    replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    if replied_message.attachments:
                        for attachment in replied_message.attachments:
                            if any(attachment.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                                image_urls.append(attachment.url)
                    
                    # Hình ảnh trong embeds của tin nhắn được reply
                    if replied_message.embeds:
                        for embed in replied_message.embeds:
                            if embed.image:
                                image_urls.append(embed.image.url)
                            if embed.thumbnail:
                                image_urls.append(embed.thumbnail.url)
                except:
                    pass
            
            # 3. Hình ảnh từ link trong prompt
            detected_url = self.detect_image_url(prompt)
            if detected_url:
                image_urls.append(detected_url)
            
            # Xử lý prompt và hình ảnh
            contents = await self.parse_prompt(prompt, image_urls)
            
            # Thử gọi API với fallback
            response_text, used_model = await self.call_gemini_with_fallback(contents)
            
            # Stream kết quả lên Discord
            await self.stream_response(response_message, response_text, len(image_urls), used_model)
            
        except Exception as e:
            error_embed = Embed(
                description=f"❌ Lỗi: {str(e)}\n¯\\_(ツ)_/¯",
                color=Color.red()
            )
            await response_message.edit(embed=error_embed)
            print(f"Error in ai command: {e}")
    
    async def parse_prompt(self, prompt: str, image_urls: list = None):
        """Xử lý prompt và ảnh qua Cloudflare Worker proxy"""
        contents = []
        
        # Thêm text prompt
        contents.append(prompt)
        
        # Xử lý ảnh qua Cloudflare Worker
        if image_urls:
            async with httpx.AsyncClient(timeout=60.0) as client:
                for url in image_urls:
                    try:
                        # Gọi Cloudflare Worker để tải ảnh
                        response = await client.post(
                            self.worker_url,
                            json={"imageUrl": url}
                        )
                        response.raise_for_status()
                        
                        # Lấy base64 data từ worker
                        result = response.json()
                        base64_data = result.get('data')
                        mime_type = result.get('mimeType', 'image/jpeg')
                        
                        if not base64_data:
                            raise Exception("Worker không trả về data")
                        
                        # Decode base64 và gửi inline
                        import base64
                        image_bytes = base64.b64decode(base64_data)
                        
                        contents.append(
                            types.Part.from_bytes(
                                data=image_bytes,
                                mime_type=mime_type
                            )
                        )
                        print(f"✅ Đã thêm ảnh qua Worker: {url[:60]}... ({len(image_bytes)} bytes)")
                    except Exception as e:
                        print(f"⚠️ Lỗi xử lý ảnh {url} qua Worker: {e}")
        
        return contents
    
    async def call_gemini_with_fallback(self, contents: list):
        """Gọi API Gemini với cơ chế fallback tự động"""
        last_error = None
        
        for model_name in self.models:
            try:
                # Gọi API với stream
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        max_output_tokens=4096,
                        temperature=0.7,
                    )
                )
                
                # Trả về text và tên model nếu thành công
                return response.text, model_name
                
            except Exception as e:
                error_str = str(e).lower()
                last_error = e
                
                # Nếu là lỗi rate limit hoặc server quá tải, thử model tiếp theo
                if '429' in error_str or '503' in error_str or 'quota' in error_str or 'rate limit' in error_str:
                    print(f"⚠️ Model {model_name} bị giới hạn, đang thử model khác...")
                    continue
                else:
                    # Nếu là lỗi khác, throw luôn
                    raise e
        
        # Nếu tất cả models đều fail
        raise Exception(f"Tất cả models đều không khả dụng. Lỗi cuối: {last_error}")
    
    def detect_image_url(self, text: str) -> str:
        """Phát hiện URL hình ảnh trong text"""
        for word in text.split():
            url_path = urlparse(word).path
            if re.search(r'\.(jpg|jpeg|png|gif|webp)$', url_path, re.IGNORECASE):
                return word
        return None
    
    async def stream_response(self, message: Message, full_text: str, image_count: int = 0, model_name: str = ""):
        """Stream response lên Discord, tự động split nếu quá dài"""
        MAX_EMBED_LENGTH = 4000  # Discord embed description limit ~4096, để buffer
        
        # Nếu response quá dài, split thành nhiều messages
        if len(full_text) > MAX_EMBED_LENGTH:
            await self.send_long_response(message, full_text, model_name)
            return
        
        # Response ngắn - stream bình thường
        embed = Embed(description="", color=Color.blue())
        
        # Thêm thông tin model vào footer
        if model_name:
            embed.set_footer(text=f"{model_name}")
        
        # Chia nhỏ text thành chunks
        chunk_size = 50  # Số ký tự mỗi chunk
        chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
        
        update_counter = 0
        for chunk in chunks:
            embed.description += chunk
            update_counter += 1
            
            # Cập nhật Discord mỗi 4 chunks để tránh rate limit
            if update_counter >= 4:
                await message.edit(embed=embed)
                update_counter = 0
                await asyncio.sleep(0.3)
        
        # Cập nhật lần cuối với màu xanh
        embed.color = Color.green()
        if model_name:
            embed.set_footer(text=f"{model_name}")
        
        await message.edit(embed=embed)
    
    async def send_long_response(self, first_message: Message, full_text: str, model_name: str = ""):
        """Gửi response dài qua nhiều messages"""
        MAX_EMBED_LENGTH = 4000
        
        # Split text thành các parts
        parts = []
        current_part = ""
        
        # Split theo dòng để tránh cắt mid-sentence
        lines = full_text.split('\n')
        
        for line in lines:
            # Nếu thêm line này vào sẽ vượt quá limit
            if len(current_part) + len(line) + 1 > MAX_EMBED_LENGTH:
                if current_part:
                    parts.append(current_part)
                    current_part = line
                else:
                    # Line đơn lẻ quá dài, phải cắt cứng
                    parts.append(line[:MAX_EMBED_LENGTH])
                    current_part = line[MAX_EMBED_LENGTH:]
            else:
                if current_part:
                    current_part += '\n' + line
                else:
                    current_part = line
        
        if current_part:
            parts.append(current_part)
        
        # Gửi part đầu tiên (edit message hiện tại)
        embed = Embed(
            description=parts[0],
            color=Color.green()
        )
        if model_name:
            embed.set_footer(text=f"{model_name} (1/{len(parts)})")
        await first_message.edit(embed=embed)
        
        # Gửi các parts còn lại (messages mới)
        for i, part in enumerate(parts[1:], start=2):
            embed = Embed(
                description=part,
                color=Color.green()
            )
            if model_name:
                embed.set_footer(text=f"{model_name} ({i}/{len(parts)})")
            
            await first_message.channel.send(embed=embed)
            await asyncio.sleep(0.5)  # Tránh rate limit



    def get_mime_type(self, url: str) -> str:
        """Xác định MIME type từ URL"""
        url_lower = url.lower()
        if url_lower.endswith('.png'):
            return 'image/png'
        elif url_lower.endswith('.gif'):
            return 'image/gif'
        elif url_lower.endswith('.webp'):
            return 'image/webp'
        else:
            return 'image/jpeg'

async def setup(bot):
    await bot.add_cog(GeminiAICommand(bot))