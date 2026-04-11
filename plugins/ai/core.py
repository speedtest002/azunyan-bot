"""plugins/ai/core.py — Gemini streaming logic and image handling"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Callable
from urllib.parse import urlparse

import yaml
import hikari
from google import genai
from google.genai import types

from core.config import settings
from plugins.ai.views import build_ai_embed, split_text

log = logging.getLogger("azunyan.ai")

PROMPTS_PATH = Path(settings.prompts_path)

with PROMPTS_PATH.open("r", encoding="utf-8") as f:
    _prompts = yaml.safe_load(f)

MODELS = [
    {"key": "gemma-4-31b-it", "id": "gemma-4-31b-it"},
    {"key": "gemma-4-26b-a4b-it", "id": "models/gemma-4-26b-a4b-it"},
]

_client = genai.Client(api_key=settings.gemini_api_key)


def detect_image_url(text: str) -> list[str]:
    """Extracts image URLs from a string."""
    return [
        w for w in text.split()
        if re.search(r"\.(jpg|jpeg|png|gif|webp)$", urlparse(w).path, re.IGNORECASE)
    ]


def guess_mime(url: str) -> str:
    """Guesses the mime type of an image URL."""
    path = urlparse(url).path.lower()
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".webp"):
        return "image/webp"
    if path.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def prepare_image_parts(urls: list[str]) -> list[types.Part]:
    """Converts image URLs to Gemini types.Part using from_uri."""
    return [
        types.Part.from_uri(file_uri=url, mime_type=guess_mime(url))
        for url in urls
    ]


def _is_rate_limit(error: Exception) -> bool:
    """Checks if an error is a rate limit error."""
    s = str(error).lower()
    if any(c in s for c in ("429", "503")):
        return True
    return any(kw in s for kw in ("resource_exhausted", "rate limit", "quota"))


async def call_gemini_stream(
    prompt: str, 
    image_parts: list[types.Part], 
    author_name: str, 
    server_name: str, 
    channel_name: str
) -> AsyncGenerator[tuple[str, int, set[str], bool], None]:
    """Yields (full_text, total_tokens, sources, is_final) tuples from Gemini."""
    system_prompt = _prompts["MainSystemPrompt"].format(
        current_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        server_name=server_name,
        channel_name=channel_name,
    )
    contents = [
        *image_parts,
        types.Part.from_text(text=f"[{author_name}]: {prompt}"),
    ]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[types.Tool(google_search=types.GoogleSearch())],
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_level="high"),
    )

    last_error = None
    for model in MODELS:
        try:
            stream = await _client.aio.models.generate_content_stream(
                model=model["id"], contents=contents, config=config
            )
            full_text = ""
            total_tokens = 0
            sources: set[str] = set()
            last_yield = 0.0

            async for chunk in stream:
                if chunk.candidates and getattr(chunk.candidates[0].content, "parts", None):
                    for part in chunk.candidates[0].content.parts:
                        if not getattr(part, "thought", False) and hasattr(part, "text") and part.text:
                            full_text += part.text

                if chunk.candidates and getattr(chunk.candidates[0], "grounding_metadata", None):
                    meta = chunk.candidates[0].grounding_metadata
                    if getattr(meta, "grounding_chunks", None):
                        for gc in meta.grounding_chunks:
                            if getattr(gc, "web", None) and gc.web.uri:
                                title = getattr(gc.web, "title", gc.web.uri)
                                sources.add(f"[{title}]({gc.web.uri})")

                if getattr(chunk, "usage_metadata", None):
                    total_tokens = chunk.usage_metadata.total_token_count or total_tokens

                now = time.time()
                if now - last_yield > 1.5 and full_text:
                    yield full_text, total_tokens, sources, False
                    last_yield = now

            yield full_text, total_tokens, sources, True
            return

        except Exception as e:
            last_error = e
            if _is_rate_limit(e):
                log.info("Rate limit hit for %s, trying next...", model['key'])
                continue
            raise

    raise Exception(f"All models failed: {last_error}")


async def process_ai_request(
    prompt: str,
    image_urls: list[str],
    author_name: str,
    server_name: str,
    channel_name: str,
    respond_fn: Callable[[hikari.Embed], Any],
    edit_fn: Callable[[hikari.Embed], Any],
    followup_fn: Callable[[hikari.Embed], Any],
) -> None:
    """Orchestrates the AI request lifecycle."""
    image_parts = prepare_image_parts(image_urls)

    # Initial response is already a placeholder from the command handler
    # but we can call respond_fn if needed. Here we assume edit_fn will be used for updates.

    try:
        async for full_text, tokens, sources, is_final in call_gemini_stream(
            prompt, image_parts, author_name, server_name, channel_name
        ):
            if is_final and len(full_text) > 4000:
                pages = split_text(full_text)
                for i, page_text in enumerate(pages):
                    page_sources = sources if i == len(pages) - 1 else set()
                    embed = build_ai_embed(page_text, "gemma", tokens, True, page_sources)
                    embed.set_footer(f"gemma | {tokens} tokens ({i+1}/{len(pages)})")
                    if i == 0:
                        await edit_fn(embed)
                    else:
                        await followup_fn(embed)
                        await asyncio.sleep(0.5)
            else:
                await edit_fn(build_ai_embed(full_text, "gemma", tokens, is_final, sources if is_final else set()))
    except Exception as e:
        log.exception("AI processing error")
        err_embed = hikari.Embed(description=f"**Lỗi:** {str(e)[:1000]}", color=0xED4245)
        try:
            await edit_fn(err_embed)
        except Exception:
            await followup_fn(err_embed)


async def collect_image_urls(
    prompt: str,
    attachments: list[hikari.Attachment] | None = None,
    referenced_message: hikari.Message | None = None,
) -> list[str]:
    """Centralized logic for gathering image URLs from various sources."""
    image_urls = []
    exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp')

    if attachments:
        for a in attachments:
            if a.filename.lower().endswith(exts):
                image_urls.append(a.url)

    if referenced_message:
        for a in referenced_message.attachments:
            if a.filename.lower().endswith(exts):
                image_urls.append(a.url)
        
        # Also check embeds for images in referenced message
        for e in referenced_message.embeds:
            if e.image:
                image_urls.append(e.image.url)
            if e.thumbnail:
                image_urls.append(e.thumbnail.url)

    detected = detect_image_url(prompt)
    if detected:
        image_urls.extend(detected)

    return list(dict.fromkeys(image_urls))
