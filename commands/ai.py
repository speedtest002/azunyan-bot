import discord
from discord.ext import commands
from discord import app_commands, Embed, Message, Color
import asyncio
import httpx
import re
import os
import time
import yaml
from urllib.parse import urlparse
from google import genai
from google.genai import types

with open('prompts.yaml', 'r', encoding='utf-8') as f:
    _prompts = yaml.safe_load(f)

MODELS = [
    { 'key': 'gemma-4-31b-it',     'id': 'gemma-4-31b-it'             },
    { 'key': 'gemma-4-26b-a4b-it', 'id': 'models/gemma-4-26b-a4b-it' },
]


class GeminiAICommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)


    @commands.hybrid_command(name="ai")
    @app_commands.describe(
        prompt='prompt',
        attachment='ảnh đính kèm',
    )
    async def ai(
        self,
        ctx: commands.Context,
        *,
        prompt: str,
        attachment: discord.Attachment = None,
    ):
        embed = Embed(description="Bot đã ngủm...", color=Color.purple())
        response_message = await ctx.send(embed=embed)

        try:
            image_urls = await self.collect_image_urls(ctx, prompt, slash_attachment=attachment)
            image_parts = await self.download_images(image_urls)
            await self.call_gemini_stream(prompt, image_parts, ctx, response_message)

        except Exception as error:
            try:
                # Nếu embed đã mất dòng chữ "Đang xử lý..." tức là đang stream dở thì gửi followup thay vì ghi đè chữ
                if len(response_message.embeds) > 0 and "Bot đã ngủm" not in (response_message.embeds[0].description or ""):
                    await ctx.send(embed=Embed(description=f"**Lỗi:** {str(error)[:1000]}", color=Color.red()))
                else:
                    await response_message.edit(
                        embed=Embed(description=f"**Lỗi:** {str(error)[:1000]}", color=Color.red())
                    )
            except Exception:
                pass
            print(f"ai error: {error}")


    async def collect_image_urls(
        self,
        ctx: commands.Context,
        prompt: str,
        slash_attachment: discord.Attachment = None,
    ) -> list[str]:
        image_urls = []
        exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

        if slash_attachment and slash_attachment.filename.lower().endswith(exts):
            image_urls.append(slash_attachment.url)

        if ctx.message.attachments:
            for a in ctx.message.attachments:
                if a.filename.lower().endswith(exts):
                    image_urls.append(a.url)

        if ctx.message.reference:
            try:
                ref = ctx.message.reference.resolved
                if not isinstance(ref, discord.Message):
                    try:
                        ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    except Exception:
                        ref = None
                        
                if ref:
                    for a in ref.attachments:
                        if a.filename.lower().endswith(exts):
                            image_urls.append(a.url)
                    for e in ref.embeds:
                        if e.image:     image_urls.append(e.image.url)
                        if e.thumbnail: image_urls.append(e.thumbnail.url)
            except Exception:
                pass

        detected = self.detect_image_url(prompt)
        if detected:
            image_urls.extend(detected)

        return list(dict.fromkeys(image_urls))

    async def download_images(self, urls: list[str]) -> list[types.Part]:
        parts = []
        async with httpx.AsyncClient(timeout=15.0) as session:
            for url in urls:
                try:
                    resp = await session.get(url)
                    resp.raise_for_status()
                    parts.append(
                        types.Part.from_bytes(
                            data=resp.content,
                            mime_type=self.guess_mime(url),
                        )
                    )
                except Exception as e:
                    print(f"Failed to download image {url}: {e}")
        return parts

    async def call_gemini_stream(
        self,
        prompt: str,
        image_parts: list[types.Part],
        ctx: commands.Context,
        message: Message,
    ):
        system_prompt = _prompts['MainSystemPrompt'].format(
            current_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            server_name=getattr(ctx.guild, 'name', 'DM'),
            channel_name=getattr(ctx.channel, 'name', 'DM'),
        )
        contents = [
            *image_parts,
            types.Part.from_text(text=f"[{ctx.author.display_name}]: {prompt}"),
        ]

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )

        last_error = None
        for model in MODELS:
            try:
                stream = await self.client.aio.models.generate_content_stream(
                    model=model['id'],
                    contents=contents,
                    config=config,
                )
                await self.stream_response(message, stream, model['key'])
                return

            except Exception as e:
                last_error = e
                if self._is_rate_limit(e):
                    print(f"Rate limit on {model['key']}, trying next...")
                    continue
                raise

        raise Exception(f"All models failed: {last_error}")

    # ── Real Streaming Display ─────────────────────────────────────────────

    async def stream_response(self, message: Message, stream, model_key: str):
        full_text      = ""
        total_tokens   = 0
        last_edit_time = 0
        sources        = set()

        async for chunk in stream:
            if chunk.candidates and getattr(chunk.candidates[0].content, 'parts', None):
                for part in chunk.candidates[0].content.parts:
                    if not getattr(part, 'thought', False) and hasattr(part, 'text') and part.text:
                        full_text += part.text
            elif chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                for part in chunk.candidates[0].content.parts:
                    if not getattr(part, 'thought', False) and hasattr(part, 'text') and part.text:
                        full_text += part.text

            if chunk.candidates and getattr(chunk.candidates[0], 'grounding_metadata', None):
                meta = chunk.candidates[0].grounding_metadata
                if getattr(meta, 'grounding_chunks', None):
                    for g_chunk in meta.grounding_chunks:
                        if getattr(g_chunk, 'web', None) and getattr(g_chunk.web, 'uri', None):
                            title = getattr(g_chunk.web, 'title', g_chunk.web.uri)
                            sources.add(f"[{title}]({g_chunk.web.uri})")

            if getattr(chunk, 'usage_metadata', None) and chunk.usage_metadata:
                total_tokens = chunk.usage_metadata.total_token_count

            now = time.time()
            if now - last_edit_time > 1.5 and full_text:
                await self._update_embed(message, full_text, model_key, total_tokens, is_final=False, sources=sources)
                last_edit_time = now

        if len(full_text) > 4000:
            await self.send_long_response(message, full_text, total_tokens, model_key, sources=sources)
        else:
            await self._update_embed(message, full_text, model_key, total_tokens, is_final=True, sources=sources)

    async def _update_embed(self, message, text, footer, tokens, is_final, sources=None):
        if sources:
            text += "\n\n**Source:**\n" + "\n".join(f"- {s}" for s in sources)
            
        display     = text if len(text) <= 4000 else text[-4000:]
        color       = Color.green() if is_final else Color.blue()
        embed       = Embed(description=display or "...", color=color)
        footer_text = f"{footer} | {tokens} tokens" if tokens else footer
        embed.set_footer(text=footer_text)
        try:
            await message.edit(embed=embed)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                await asyncio.sleep(e.retry_after or 1)
        except Exception:
            pass

    # ── Long Response ──────────────────────────────────────────────────────

    async def send_long_response(self, message: Message, text: str, tokens: int, model: str, sources: set = None):
        if sources:
            text += "\n\n**Nguồn trích dẫn:**\n" + "\n".join(f"- {s}" for s in sources)

        max_length   = 4000
        parts        = []
        current_part = ""

        for line in text.split('\n'):
            if len(line) > max_length:
                if current_part:
                    parts.append(current_part)
                    current_part = ""
                for i in range(0, len(line), max_length):
                    parts.append(line[i:i+max_length])
                continue

            if len(current_part) + len(line) + 1 > max_length:
                if current_part:
                    parts.append(current_part)
                current_part = line
            else:
                current_part = current_part + '\n' + line if current_part else line
                
        if current_part:
            parts.append(current_part)

        footer_text = f"{model} | {tokens} tokens" if tokens else model
        total_parts = len(parts)

        first_embed = Embed(description=parts[0], color=Color.green())
        first_embed.set_footer(text=f"{footer_text} (1/{total_parts})")
        await message.edit(embed=first_embed)

        for index, part in enumerate(parts[1:], start=2):
            embed = Embed(description=part, color=Color.green())
            embed.set_footer(text=f"{footer_text} ({index}/{total_parts})")
            await message.channel.send(embed=embed)
            await asyncio.sleep(0.5)

    # ── Utilities ──────────────────────────────────────────────────────────

    @staticmethod
    def _is_rate_limit(error: Exception) -> bool:
        err_str = str(error).lower()
        if any(c in err_str for c in ('429', '503')):
            return True
        if any(kw in err_str for kw in ('resource_exhausted', 'rate limit', 'quota')):
            return True
        if hasattr(error, 'status_code') and error.status_code in (429, 503):
            return True
        return False

    def detect_image_url(self, text: str) -> list[str]:
        urls = []
        for word in text.split():
            if re.search(r'\.(jpg|jpeg|png|gif|webp)$', urlparse(word).path, re.IGNORECASE):
                urls.append(word)
        return urls

    def guess_mime(self, url: str) -> str:
        p = urlparse(url).path.lower()
        if p.endswith('.png'):  return 'image/png'
        if p.endswith('.webp'): return 'image/webp'
        if p.endswith('.gif'):  return 'image/gif'
        return 'image/jpeg'


async def setup(bot):
    await bot.add_cog(GeminiAICommand(bot))