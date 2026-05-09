"""plugins/ai/core.py — Gemini streaming logic and image handling"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable
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
    {"name": "gemma-4-31b-it", "model": "models/gemma-4-31b-it", "tools": ["search"], "thinking_level": "high"},
    {"name": "gemma-4-26b-a4b-it", "model": "models/gemma-4-26b-a4b-it", "tools": ["search"], "thinking_level": "high"},
    {"name": "gemini-3.1-flash-lite-preview", "model": "models/gemini-3.1-flash-lite-preview", "tools": ["map"], "thinking_level": "high"},
]

PROXY_URL = settings.cloudflare_worker_url

_client_kwargs: dict[str, Any] = {"api_key": settings.gemini_api_key}
if PROXY_URL:
    base_url = PROXY_URL if PROXY_URL.endswith("/gemini") else f"{PROXY_URL.rstrip('/')}/gemini"
    _client_kwargs["http_options"] = types.HttpOptions(base_url=base_url)

_client = genai.Client(**_client_kwargs)


def detect_image_url(text: str) -> list[str]:
    return [
        w for w in text.split()
        if re.search(r"\.(jpg|jpeg|png|gif|webp)$", urlparse(w).path, re.IGNORECASE)
    ]


def guess_mime(url: str) -> str:
    path = urlparse(url).path.lower()
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".webp"):
        return "image/webp"
    if path.endswith(".gif"):
        return "image/gif"  
    return "image/jpeg"


def _is_rate_limit(error: Exception) -> bool:
    """Checks if an error is a rate limit error."""
    s = str(error).lower()
    if any(c in s for c in ("429", "503", "500")):
        return True
    return any(kw in s for kw in ("resource_exhausted", "rate limit", "quota", "internal error"))


async def process_ai_request(
    prompt: str,
    image_urls: list[str],
    author_name: str,
    server_name: str,
    channel_name: str,
    respond_fn: Callable[[hikari.Embed], Any],
    edit_fn: Callable[[hikari.Embed], Any],
    followup_fn: Callable[[hikari.Embed], Any],
    thinking_fn: Callable[[], Any] | None = None,
) -> None:
    try:
        image_parts = [
            types.Part.from_uri(file_uri=url, mime_type=guess_mime(url))
            for url in image_urls
        ]
        
        system_prompt = "<|think|>\n" + _prompts["MainSystemPrompt"].format(
            current_time=datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
            server_name=server_name,
            channel_name=channel_name,
        )
        contents = [
            types.Part.from_text(text=f"{author_name}: {prompt}"),
            *image_parts,
        ]
        last_error = None
        for model in MODELS:
            model_name = model["name"]
            thinking_level = model.get("thinking_level", "minimal")

            tool_list = []
            for t in model.get("tools", []):
                if t == "search":
                    tool_list.append(types.Tool(google_search=types.GoogleSearch()))

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tool_list or None,
                thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_level=thinking_level),
            )

            try:
                stream = await _client.aio.models.generate_content_stream(
                    model=model["model"], contents=contents, config=config
                )
                full_text = ""
                total_tokens = 0
                sources: set[str] = set()
                last_yield = 0.0
                thinking_notified = False

                async for chunk in stream:
                    if chunk.candidates:
                        candidate = chunk.candidates[0]
                        if getattr(candidate.content, "parts", None):
                            for part in candidate.content.parts:
                                if getattr(part, "thought", False):
                                    if not thinking_notified and thinking_fn:
                                        await thinking_fn()
                                        thinking_notified = True
                                elif hasattr(part, "text") and part.text:
                                    full_text += part.text

                        if getattr(candidate, "grounding_metadata", None):
                            meta = candidate.grounding_metadata
                            if getattr(meta, "grounding_chunks", None):
                                for gc in meta.grounding_chunks:
                                    if getattr(gc, "web", None) and gc.web.uri:
                                        title = getattr(gc.web, "title", gc.web.uri)
                                        sources.add(f"[{title}]({gc.web.uri})")

                    if getattr(chunk, "usage_metadata", None):
                        total_tokens = chunk.usage_metadata.total_token_count or total_tokens

                    now = time.time()
                    if now - last_yield > 1.5 and full_text:
                        await edit_fn(build_ai_embed(full_text, model_name, total_tokens, False, set()))
                        last_yield = now

                if len(full_text) > 4000:
                    pages = split_text(full_text)
                    for i, page_text in enumerate(pages):
                        page_sources = sources if i == len(pages) - 1 else set()
                        embed = build_ai_embed(page_text, model_name, total_tokens, True, page_sources)
                        embed.set_footer(f"{model_name} | {total_tokens} tokens ({i+1}/{len(pages)})")
                        if i == 0:
                            await edit_fn(embed)
                        else:
                            await followup_fn(embed)
                            await asyncio.sleep(0.5)
                else:
                    await edit_fn(build_ai_embed(full_text, model_name, total_tokens, True, sources))

                return

            except Exception as e:
                last_error = e
                log.warning("Error on %s: %s — trying next model...", model_name, e)
                continue

        raise Exception(f"All models failed: {last_error}")

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
