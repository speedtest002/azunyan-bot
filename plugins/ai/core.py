"""plugins/ai/core.py — Gemini streaming logic, hot-reload model config, cooldowns, and image handling"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import inspect
import logging
from pathlib import Path
import re
import time
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import aiohttp
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
import hikari
import yaml

from core.config import settings
from plugins.ai.views import (
    AIPaginationView,
    MAX_EMBED_LEN,
    build_ai_embed,
    build_source_components,
    sanitize_sources,
    split_text,
)

log = logging.getLogger("azunyan.ai")

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".jfif")
_IMAGE_EXT_RE = re.compile(r"\.(jpg|jpeg|png|gif|webp|bmp|jfif)$", re.IGNORECASE)
_QUERY_FORMAT_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
    "bmp": "image/bmp",
}
_URL_STRIP_CHARS = "<>()[]\"'`,;."
_MAX_IMAGE_COUNT = 5
_MAX_IMAGE_BYTES = 15 * 1024 * 1024  # 15 MB mỗi ảnh
_IMAGE_DOWNLOAD_TIMEOUT = 15.0
_STREAM_EDIT_INTERVAL = 1.5

_NO_SEARCH_NOTICE = (
    "\n\n=== LƯU Ý CÔNG CỤ (BẮT BUỘC) ===\n"
    "- Công cụ web search (Google Search) hiện ĐANG TẮT cho lượt trả lời này.\n"
    "- TUYỆT ĐỐI KHÔNG nói là đã tra cứu/tìm kiếm web và KHÔNG bịa thông tin thời gian thực "
    "(thời tiết, tin tức mới, tỷ giá, sự kiện gần đây...).\n"
    "- Nếu câu hỏi đòi hỏi dữ liệu thời gian thực hoặc bạn không chắc chắn, hãy trả lời thẳng thắn "
    "rằng hiện không thể tra cứu web để kiểm chứng."
)


@dataclass(frozen=True, slots=True)
class ModelConfig:
    name: str
    model: str
    tools: tuple[str, ...] = ()
    thinking_level: str | None = None
    thinking_budget: int | None = None
    include_thoughts: bool = True
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class AISettings:
    request_timeout_seconds: float = 30.0
    stream_chunk_timeout_seconds: float = 45.0
    cooldown_seconds: float = 60.0
    max_cooldown_seconds: float = 300.0


@dataclass(frozen=True, slots=True)
class AIConfig:
    models: tuple[ModelConfig, ...]
    settings: AISettings = field(default_factory=AISettings)


_DEFAULT_AI_CONFIG = AIConfig(
    models=(
        ModelConfig(
            name="gemma-4-31b-it",
            model="models/gemma-4-31b-it",
            tools=("search",),
            thinking_level="minimal",
        ),
        ModelConfig(
            name="gemini-4-hydrogen",
            model="models/gemini-4-hydrogen",
            tools=(),
            thinking_level="medium",
        ),
        ModelConfig(
            name="gemma-4-26b-a4b-it",
            model="models/gemma-4-26b-a4b-it",
            tools=("search",),
            thinking_level="minimal",
        ),
        ModelConfig(
            name="gemini-2.5-flash",
            model="models/gemini-2.5-flash",
            tools=("search",),
            thinking_budget=-1,
        ),
        ModelConfig(
            name="gemini-2.5-flash-lite",
            model="models/gemini-2.5-flash-lite",
            tools=("search",),
            thinking_budget=0,
            include_thoughts=False,
        ),
        ModelConfig(
            name="gemini-3.8-flash",
            model="models/gemini-3.8-flash",
            tools=(),
            thinking_level="medium",
        ),
        ModelConfig(
            name="gemini-3.5-flash-lite",
            model="models/gemini-3.5-flash-lite",
            tools=(),
            thinking_level="medium",
        ),
    ),
    settings=AISettings(),
)

# Hot-reload caches (keyed by file mtime_ns)
_prompts_cache: dict[str, Any] = {}
_prompts_mtime_ns: int | None = None

_ai_config_cache: AIConfig | None = None
_ai_config_mtime_ns: int | None = None

# In-memory per-model cooldown: model_id -> (cooldown_until_monotonic, consecutive_failures)
_model_cooldowns: dict[str, tuple[float, int]] = {}

# Lazy GenAI client
_client: genai.Client | None = None


class _EmptyModelResponseError(RuntimeError):
    """Raised when a model finishes streaming without returning any visible text."""


def _parse_positive_float(value: Any, default: float, *, minimum: float = 1.0) -> float:
    try:
        parsed = float(value)
        if parsed >= minimum:
            return parsed
    except (TypeError, ValueError):
        pass
    return default


def _parse_ai_config(raw: Any) -> AIConfig:
    if isinstance(raw, list):
        raw_models = raw
        raw_settings: dict[str, Any] = {}
    elif isinstance(raw, dict):
        raw_models = raw.get("models", [])
        raw_settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    else:
        raise ValueError("ai_models.yaml must be a mapping or list of models")

    if not isinstance(raw_models, list):
        raise ValueError("'models' in ai_models.yaml must be a list")

    ai_settings = AISettings(
        request_timeout_seconds=_parse_positive_float(
            raw_settings.get("request_timeout_seconds"), 30.0, minimum=5.0
        ),
        stream_chunk_timeout_seconds=_parse_positive_float(
            raw_settings.get("stream_chunk_timeout_seconds"), 45.0, minimum=5.0
        ),
        cooldown_seconds=_parse_positive_float(
            raw_settings.get("cooldown_seconds"), 60.0, minimum=0.0
        ),
        max_cooldown_seconds=_parse_positive_float(
            raw_settings.get("max_cooldown_seconds"), 300.0, minimum=0.0
        ),
    )

    models: list[ModelConfig] = []
    for idx, item in enumerate(raw_models):
        if not isinstance(item, dict):
            log.warning("Skipping invalid model entry #%d in ai_models.yaml (expected dict)", idx)
            continue

        if item.get("enabled", True) is False:
            continue

        model_id = str(item.get("model") or "").strip()
        if not model_id:
            log.warning("Skipping model entry #%d in ai_models.yaml (missing 'model')", idx)
            continue

        name = str(item.get("name") or model_id.removeprefix("models/")).strip()
        raw_tools = item.get("tools") or []
        tools = tuple(str(t).strip().lower() for t in raw_tools if str(t).strip()) if isinstance(raw_tools, list) else ()

        thinking_level = item.get("thinking_level")
        thinking_level_str = str(thinking_level).strip().lower() if thinking_level is not None and str(thinking_level).strip() else None

        thinking_budget_val = item.get("thinking_budget")
        thinking_budget_int: int | None = None
        if thinking_budget_val is not None:
            try:
                thinking_budget_int = int(thinking_budget_val)
            except (TypeError, ValueError):
                log.warning("Invalid thinking_budget=%r for model %s; ignoring", thinking_budget_val, name)

        include_thoughts = bool(item.get("include_thoughts", True))

        models.append(
            ModelConfig(
                name=name,
                model=model_id,
                tools=tools,
                thinking_level=thinking_level_str,
                thinking_budget=thinking_budget_int,
                include_thoughts=include_thoughts,
                enabled=True,
            )
        )

    if not models:
        raise ValueError("No enabled models found in ai_models.yaml")

    return AIConfig(models=tuple(models), settings=ai_settings)


def get_ai_config(path: Path | None = None) -> AIConfig:
    """Load AI model config from YAML with mtime-based hot reload."""
    global _ai_config_cache, _ai_config_mtime_ns

    config_path = path or Path(settings.ai_models_path)
    try:
        mtime_ns = config_path.stat().st_mtime_ns
    except OSError as exc:
        if _ai_config_cache is None:
            log.warning("Cannot access %s (%s) — using built-in default models", config_path, exc)
            _ai_config_cache = _DEFAULT_AI_CONFIG
        return _ai_config_cache

    if _ai_config_cache is not None and _ai_config_mtime_ns == mtime_ns and path is None:
        return _ai_config_cache

    try:
        with config_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        parsed = _parse_ai_config(raw)
        if path is None:
            is_reload = _ai_config_cache is not None
            _ai_config_cache = parsed
            _ai_config_mtime_ns = mtime_ns
            # Dọn cooldown cho các model không còn nằm trong config mới
            active_ids = {m.model for m in parsed.models}
            for stale_id in list(_model_cooldowns):
                if stale_id not in active_ids:
                    _model_cooldowns.pop(stale_id, None)
            if is_reload:
                log.info(
                    "Reloaded %s (%d enabled models: %s)",
                    config_path,
                    len(parsed.models),
                    ", ".join(m.name for m in parsed.models),
                )
        return parsed
    except Exception as exc:
        log.warning("Failed to parse %s: %s — keeping previous config", config_path, exc)
        if _ai_config_cache is None:
            _ai_config_cache = _DEFAULT_AI_CONFIG
        return _ai_config_cache


def get_prompts(path: Path | None = None) -> dict[str, Any]:
    """Load prompts.yaml with mtime-based hot reload."""
    global _prompts_cache, _prompts_mtime_ns

    prompts_path = path or Path(settings.prompts_path)
    try:
        mtime_ns = prompts_path.stat().st_mtime_ns
    except OSError as exc:
        if not _prompts_cache:
            log.warning("Cannot access %s (%s)", prompts_path, exc)
        return _prompts_cache

    if _prompts_cache and _prompts_mtime_ns == mtime_ns and path is None:
        return _prompts_cache

    try:
        with prompts_path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            raise ValueError("prompts.yaml root must be a mapping")
        if path is None:
            is_reload = bool(_prompts_cache)
            _prompts_cache = loaded
            _prompts_mtime_ns = mtime_ns
            if is_reload:
                log.info("Reloaded %s", prompts_path)
        return loaded
    except Exception as exc:
        log.warning("Failed to parse %s: %s — keeping previous prompts", prompts_path, exc)
        return _prompts_cache


def get_genai_client() -> genai.Client:
    """Lazily create and cache the shared Google GenAI client."""
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError("Bot chưa được cấu hình GEMINI_API_KEY.")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def close_ai_client() -> None:
    """Close underlying async HTTP sessions owned by the GenAI client."""
    global _client
    if _client is not None:
        try:
            await _client.aio.aclose()
        except Exception as exc:
            log.debug("Error closing GenAI async client: %s", exc)
        _client = None


def reset_model_cooldowns() -> None:
    """Clear all in-memory model cooldowns."""
    _model_cooldowns.clear()


def _select_ordered_models(models: tuple[ModelConfig, ...]) -> list[ModelConfig]:
    """Return healthy models first (in config order), then cooling-down models by earliest expiry."""
    now = time.monotonic()
    ready: list[ModelConfig] = []
    cooling: list[tuple[float, ModelConfig]] = []

    for model in models:
        state = _model_cooldowns.get(model.model)
        if state is None or state[0] <= now:
            ready.append(model)
        else:
            cooling.append((state[0], model))

    cooling.sort(key=lambda pair: pair[0])
    return ready + [m for _, m in cooling]


def _classify_cooldown(error: Exception) -> tuple[bool, bool]:
    """Return (should_cooldown, is_not_found) for a model failure."""
    if isinstance(error, (TimeoutError, asyncio.TimeoutError, aiohttp.ClientError, ConnectionError)):
        return True, False
    if isinstance(error, _EmptyModelResponseError):
        return True, False
    if isinstance(error, genai_errors.ServerError):
        return True, False
    if isinstance(error, genai_errors.ClientError):
        code = getattr(error, "code", None)
        if code == 429:
            return True, False
        if code == 404:
            return True, True
        return False, False

    s = str(error).lower()
    if any(code in s for code in ("429", "503", "500", "504")):
        return True, False
    if any(kw in s for kw in ("resource_exhausted", "rate limit", "quota", "unavailable", "overloaded", "internal error")):
        return True, False
    return False, False


def _record_model_failure(model_id: str, ai_settings: AISettings, *, is_not_found: bool = False) -> float:
    base = ai_settings.cooldown_seconds
    max_cd = max(ai_settings.max_cooldown_seconds, base)
    if base <= 0:
        return 0.0

    _, prev_failures = _model_cooldowns.get(model_id, (0.0, 0))
    failures = prev_failures + 1
    duration = max_cd if is_not_found else min(base * (2 ** (failures - 1)), max_cd)
    _model_cooldowns[model_id] = (time.monotonic() + duration, failures)
    return duration


def _record_model_success(model_id: str) -> None:
    _model_cooldowns.pop(model_id, None)


def detect_image_url(text: str) -> list[str]:
    """Extract valid http(s) image URLs from free-form text."""
    urls: list[str] = []
    for raw_word in text.split():
        word = raw_word.strip(_URL_STRIP_CHARS)
        if not word:
            continue
        parsed = urlparse(word)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        if _IMAGE_EXT_RE.search(parsed.path):
            urls.append(word)
            continue
        # Hỗ trợ URL ảnh dạng query ?format=jpg|png|webp (vd: pbs.twimg.com)
        fmt_vals = parse_qs(parsed.query).get("format")
        if fmt_vals and fmt_vals[0].lower() in _QUERY_FORMAT_MIME:
            urls.append(word)
    return urls


def guess_mime(url: str, content_type: str | None = None) -> str:
    """Determine image MIME type from HTTP Content-Type header or URL."""
    if content_type:
        mime = content_type.split(";", 1)[0].strip().lower()
        if mime == "image/jpg":
            return "image/jpeg"
        if mime.startswith("image/"):
            return mime

    parsed = urlparse(url)
    fmt_vals = parse_qs(parsed.query).get("format")
    if fmt_vals and fmt_vals[0].lower() in _QUERY_FORMAT_MIME:
        return _QUERY_FORMAT_MIME[fmt_vals[0].lower()]

    path = parsed.path.lower()
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".webp"):
        return "image/webp"
    if path.endswith(".gif"):
        return "image/gif"
    if path.endswith(".bmp"):
        return "image/bmp"
    return "image/jpeg"


def _is_image_attachment(attachment: hikari.Attachment) -> bool:
    media_type = (getattr(attachment, "media_type", None) or "").lower()
    if media_type.startswith("image/"):
        return True
    filename = (getattr(attachment, "filename", None) or "").lower()
    return filename.endswith(_IMAGE_EXTS)


async def collect_image_urls(
    prompt: str,
    attachments: list[hikari.Attachment] | None = None,
    referenced_message: hikari.Message | None = None,
) -> list[str]:
    """Gather deduplicated http(s) image URLs from attachments, referenced message, and prompt."""
    image_urls: list[str] = []

    if attachments:
        for att in attachments:
            if _is_image_attachment(att) and att.url:
                image_urls.append(att.url)

    if referenced_message:
        for att in referenced_message.attachments:
            if _is_image_attachment(att) and att.url:
                image_urls.append(att.url)

        for emb in referenced_message.embeds:
            if emb.image and emb.image.url:
                image_urls.append(emb.image.url)
            if emb.thumbnail and emb.thumbnail.url:
                image_urls.append(emb.thumbnail.url)

    image_urls.extend(detect_image_url(prompt))

    valid_urls: list[str] = []
    seen: set[str] = set()
    for url in image_urls:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        if url not in seen:
            seen.add(url)
            valid_urls.append(url)
    return valid_urls


async def _download_single_image(
    session: aiohttp.ClientSession,
    url: str,
    *,
    max_bytes: int = _MAX_IMAGE_BYTES,
) -> types.Part | None:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AzunyanBot/1.0)"}
    timeout = aiohttp.ClientTimeout(total=_IMAGE_DOWNLOAD_TIMEOUT)
    try:
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            if resp.status != 200:
                log.warning("Image download failed (%s): HTTP %s", url, resp.status)
                return None

            content_type = resp.headers.get("Content-Type", "")
            clean_ct = content_type.split(";", 1)[0].strip().lower()
            if clean_ct and not clean_ct.startswith("image/") and clean_ct != "application/octet-stream":
                log.warning("Skipping non-image URL %s (Content-Type=%s)", url, clean_ct)
                return None

            content_length = resp.headers.get("Content-Length")
            if content_length and content_length.isdigit() and int(content_length) > max_bytes:
                log.warning("Skipping oversized image %s (%s bytes)", url, content_length)
                return None

            buf = bytearray()
            async for chunk in resp.content.iter_chunked(64 * 1024):
                buf.extend(chunk)
                if len(buf) > max_bytes:
                    log.warning("Skipping oversized image %s (> %d bytes)", url, max_bytes)
                    return None

            if not buf:
                return None

            mime_type = guess_mime(url, content_type)
            return types.Part.from_bytes(data=bytes(buf), mime_type=mime_type)
    except Exception as exc:
        log.warning("Failed to download image %s: %s", url, exc)
        return None


async def download_images(
    image_urls: list[str],
    http_session: aiohttp.ClientSession | None = None,
    *,
    max_images: int = _MAX_IMAGE_COUNT,
    max_bytes: int = _MAX_IMAGE_BYTES,
) -> list[types.Part]:
    """Download image URLs into inline GenAI Parts, skipping broken or oversized images."""
    if not image_urls:
        return []

    targets = image_urls[:max_images]
    owns_session = http_session is None or http_session.closed
    session = aiohttp.ClientSession() if owns_session else http_session
    try:
        results = await asyncio.gather(
            *(_download_single_image(session, url, max_bytes=max_bytes) for url in targets)
        )
        return [part for part in results if part is not None]
    finally:
        if owns_session:
            await session.close()


def _build_system_prompt(
    *,
    author_name: str,
    server_name: str,
    channel_name: str,
    has_search: bool,
) -> str:
    prompts = get_prompts()
    template = prompts.get("MainSystemPrompt")
    if not isinstance(template, str) or not template.strip():
        system_prompt = (
            f"Bạn là Nakano Azusa, trợ lý trên server Discord {server_name} (#{channel_name}). "
            f"Người dùng hiện tại: {author_name}."
        )
    else:
        try:
            system_prompt = template.format(
                current_time=datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S"),
                server_name=server_name,
                channel_name=channel_name,
                username=author_name,
            )
        except Exception as exc:
            log.warning("Failed to format MainSystemPrompt (%s) — using raw template", exc)
            system_prompt = template

    if not has_search:
        system_prompt += _NO_SEARCH_NOTICE

    return system_prompt


def _build_generate_config(model: ModelConfig, system_prompt: str) -> types.GenerateContentConfig:
    tool_list: list[types.Tool] = []
    if "search" in model.tools:
        tool_list.append(types.Tool(google_search=types.GoogleSearch()))

    thinking_config: types.ThinkingConfig | None = None
    if model.thinking_level is not None:
        thinking_config = types.ThinkingConfig(
            include_thoughts=model.include_thoughts,
            thinking_level=model.thinking_level,
        )
    elif model.thinking_budget is not None:
        thinking_config = types.ThinkingConfig(
            include_thoughts=model.include_thoughts,
            thinking_budget=model.thinking_budget,
        )

    return types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=tool_list or None,
        thinking_config=thinking_config,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


async def _safe_notify_thinking(
    thinking_fn: Callable[..., Any] | None,
    status_text: str | None = None,
) -> None:
    if thinking_fn is None:
        return
    try:
        if status_text is not None:
            sig = inspect.signature(thinking_fn)
            if len(sig.parameters) >= 1:
                await thinking_fn(status_text)
                return
        await thinking_fn()
    except Exception as exc:
        log.debug("Thinking status update failed (ignored): %s", exc)


async def _stream_single_model(
    *,
    client: genai.Client,
    model: ModelConfig,
    contents: list[types.Part],
    config: types.GenerateContentConfig,
    ai_settings: AISettings,
    edit_fn: Callable[..., Any],
    thinking_fn: Callable[..., Any] | None,
    stream_state: dict[str, bool],
) -> tuple[str, int, list[tuple[str, str]]]:
    """Stream content from one model. Returns (full_text, total_tokens, clean_sources)."""
    stream = await asyncio.wait_for(
        client.aio.models.generate_content_stream(
            model=model.model,
            contents=contents,
            config=config,
        ),
        timeout=ai_settings.request_timeout_seconds,
    )

    full_text = ""
    total_tokens = 0
    raw_sources: list[tuple[str | None, str | None]] = []
    last_yield = 0.0
    last_edited_len = 0
    thinking_notified = False
    finish_reason: str | None = None

    stream_iter = aiter(stream)
    try:
        while True:
            try:
                chunk = await asyncio.wait_for(
                    anext(stream_iter),
                    timeout=ai_settings.stream_chunk_timeout_seconds,
                )
            except StopAsyncIteration:
                break

            if chunk.candidates:
                candidate = chunk.candidates[0]
                if candidate.finish_reason is not None:
                    finish_reason = str(candidate.finish_reason)

                content = candidate.content
                parts = getattr(content, "parts", None) if content is not None else None
                if parts:
                    for part in parts:
                        if getattr(part, "thought", False):
                            if not thinking_notified:
                                await _safe_notify_thinking(thinking_fn)
                                thinking_notified = True
                        elif getattr(part, "text", None):
                            full_text += part.text

                grounding = getattr(candidate, "grounding_metadata", None)
                grounding_chunks = getattr(grounding, "grounding_chunks", None) if grounding else None
                if grounding_chunks:
                    for gc in grounding_chunks:
                        web = getattr(gc, "web", None)
                        uri = getattr(web, "uri", None) if web else None
                        if uri:
                            raw_sources.append((getattr(web, "title", None), uri))

            usage = getattr(chunk, "usage_metadata", None)
            if usage and usage.total_token_count:
                total_tokens = usage.total_token_count

            now = time.monotonic()
            if (
                now - last_yield >= _STREAM_EDIT_INTERVAL
                and len(full_text) != last_edited_len
                and full_text.strip()
            ):
                try:
                    await edit_fn(build_ai_embed(full_text, model.name, total_tokens, False))
                    stream_state["did_stream_edit"] = True
                    last_edited_len = len(full_text)
                except Exception as exc:
                    # Lỗi edit Discord trung gian (429/network) KHÔNG được phép làm hủy stream Gemini
                    log.debug("Intermediate stream edit skipped: %s", exc)
                last_yield = now
    finally:
        aclose = getattr(stream, "aclose", None)
        if callable(aclose):
            try:
                await aclose()
            except Exception:
                pass

    if not full_text.strip():
        raise _EmptyModelResponseError(
            f"{model.name} không trả về nội dung (finish_reason={finish_reason})"
        )

    clean_sources = sanitize_sources(raw_sources)
    return full_text, total_tokens, clean_sources


async def _deliver_final_response(
    *,
    full_text: str,
    model_name: str,
    total_tokens: int,
    sources: list[tuple[str, str]],
    author_id: int,
    edit_fn: Callable[..., Any],
    followup_fn: Callable[..., Any],
    paginate_fn: Callable[[Any], Any] | None,
) -> None:
    """Deliver final response to Discord (isolated from model fallback loop)."""
    if len(full_text) > MAX_EMBED_LEN:
        pages = split_text(full_text, MAX_EMBED_LEN)
        if author_id and paginate_fn:
            view = AIPaginationView(pages, model_name, total_tokens, sources, author_id)
            try:
                await paginate_fn(view)
                return
            except Exception as exc:
                if sources:
                    # Nếu LinkButton nguồn gây lỗi Discord (edge case), thử lại không kèm nút nguồn
                    log.warning("Pagination with sources failed (%s) — retrying without source buttons", exc)
                    fallback_view = AIPaginationView(pages, model_name, total_tokens, [], author_id)
                    await paginate_fn(fallback_view)
                    return
                raise

        for i, page_text in enumerate(pages):
            embed = build_ai_embed(page_text, model_name, total_tokens, True)
            base_footer = f"{model_name} | {total_tokens} tokens" if total_tokens else model_name
            embed.set_footer(text=f"{base_footer} ({i + 1}/{len(pages)})")
            comps = build_source_components(sources) if i == len(pages) - 1 and sources else None
            if i == 0:
                await edit_fn(embed, components=comps or None)
            else:
                await followup_fn(embed, components=comps or None)
                await asyncio.sleep(0.5)
        return

    embed = build_ai_embed(full_text, model_name, total_tokens, True)
    comps = build_source_components(sources) if sources else None
    try:
        await edit_fn(embed, components=comps or None)
    except Exception as exc:
        if comps:
            log.warning("Final edit with source buttons failed (%s) — retrying without components", exc)
            await edit_fn(embed, components=None)
        else:
            raise


async def process_ai_request(
    prompt: str,
    image_urls: list[str],
    author_name: str,
    server_name: str,
    channel_name: str,
    respond_fn: Callable[..., Any] | None = None,
    edit_fn: Callable[..., Any] | None = None,
    followup_fn: Callable[..., Any] | None = None,
    thinking_fn: Callable[..., Any] | None = None,
    author_id: int = 0,
    guild_id: int | None = None,
    channel_id: int | None = None,
    paginate_fn: Callable[[Any], Any] | None = None,
    http_session: aiohttp.ClientSession | None = None,
) -> None:
    if edit_fn is None or followup_fn is None:
        raise ValueError("edit_fn and followup_fn are required")

    try:
        ai_config = get_ai_config()
        client = get_genai_client()

        image_parts = await download_images(image_urls, http_session=http_session)
        prompt_text = prompt.strip() or "Hãy mô tả hoặc giải đáp về hình ảnh đính kèm."
        contents: list[types.Part] = [
            types.Part.from_text(text=f"{author_name}: {prompt_text}"),
            *image_parts,
        ]

        ordered_models = _select_ordered_models(ai_config.models)
        result: tuple[str, int, list[tuple[str, str]], str] | None = None
        last_error: Exception | None = None
        streamed_partial = False

        for model in ordered_models:
            has_search = "search" in model.tools
            system_prompt = _build_system_prompt(
                author_name=author_name,
                server_name=server_name,
                channel_name=channel_name,
                has_search=has_search,
            )
            config = _build_generate_config(model, system_prompt)

            if streamed_partial:
                await _safe_notify_thinking(thinking_fn, "✦ Model gặp sự cố, đang thử model khác...")
                streamed_partial = False

            stream_state = {"did_stream_edit": False}
            try:
                full_text, total_tokens, clean_sources = await _stream_single_model(
                    client=client,
                    model=model,
                    contents=contents,
                    config=config,
                    ai_settings=ai_config.settings,
                    edit_fn=edit_fn,
                    thinking_fn=thinking_fn,
                    stream_state=stream_state,
                )
                _record_model_success(model.model)
                result = (full_text, total_tokens, clean_sources, model.name)
                break
            except Exception as exc:
                last_error = exc
                should_cd, is_not_found = _classify_cooldown(exc)
                cd_str = ""
                if should_cd:
                    cd = _record_model_failure(model.model, ai_config.settings, is_not_found=is_not_found)
                    if cd > 0:
                        cd_str = f" (cooldown {int(cd)}s)"
                log.warning("Error on %s%s: %s — trying next model...", model.name, cd_str, exc)
                # Chỉ báo chuyển model khi model cũ đã thực sự stream text ra Discord
                streamed_partial = stream_state["did_stream_edit"]
                continue

        if result is None:
            if last_error is None:
                raise RuntimeError("Không model nào trả về nội dung — vui lòng thử lại.")
            raise RuntimeError(
                "Không model nào trả lời được — vui lòng thử lại sau ít phút."
            ) from last_error

        full_text, total_tokens, clean_sources, winner_model = result
        await _deliver_final_response(
            full_text=full_text,
            model_name=winner_model,
            total_tokens=total_tokens,
            sources=clean_sources,
            author_id=author_id,
            edit_fn=edit_fn,
            followup_fn=followup_fn,
            paginate_fn=paginate_fn,
        )

    except Exception as exc:
        log.exception("AI processing error")
        err_embed = hikari.Embed(description=f"**Lỗi:** {str(exc)[:1000]}", color=0xED4245)
        try:
            await edit_fn(err_embed)
        except Exception:
            try:
                await followup_fn(err_embed)
            except Exception as send_exc:
                log.warning("Failed to deliver AI error embed: %s", send_exc)
