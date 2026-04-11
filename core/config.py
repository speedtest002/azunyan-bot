from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default

    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name!r} must be an integer.") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str
    bot_owner_id: int | None
    prefix: str
    mongo_uri: str
    mongo_db_name: str
    gemini_api_key: str
    api_base_url: str
    bot_secret: str
    anisongdb_url: str
    media_url: str
    amq_guild_id: int
    prompts_path: str
    log_dir: str


def load_settings() -> Settings:
    owner_id = _get_int("BOT_OWNER_ID", 0) or None
    
    # Mặc định tìm file prompts.yaml ở thư mục gốc nếu không có cấu hình PROMPTS_PATH
    default_prompts = str(Path(__file__).resolve().parents[1] / "prompts.yaml")

    return Settings(
        discord_token=os.getenv("DISCORD_TOKEN", ""),
        bot_owner_id=owner_id,
        prefix=os.getenv("PREFIX", "azu"),
        mongo_uri=os.getenv("MONGO_URI", ""),
        mongo_db_name=os.getenv("MONGO_DB_NAME", "azunyan-bot"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        api_base_url=os.getenv("API_BASE_URL", ""),
        bot_secret=os.getenv("BOT_SECRET", ""),
        anisongdb_url=os.getenv("ANISONGDB_URL", ""),
        media_url=os.getenv("MEDIA_URL", ""),
        amq_guild_id=_get_int("AMQ_GUILD_ID", 1361617403112460389),
        prompts_path=os.getenv("PROMPTS_PATH", default_prompts),
        log_dir=os.getenv("LOG_DIR", "logs"),
    )


settings = load_settings()
...
AMQ_GUILD_ID: int = settings.amq_guild_id
PROMPTS_PATH: str = settings.prompts_path
LOG_DIR: str = settings.log_dir
BOT_OWNER_ID: int = settings.bot_owner_id or 0
PREFIX: str = settings.prefix
MONGO_URI: str = settings.mongo_uri
GEMINI_API_KEY: str = settings.gemini_api_key
API_BASE_URL: str = settings.api_base_url
BOT_SECRET: str = settings.bot_secret
ANISONGDB_URL: str = settings.anisongdb_url
MEDIA_URL: str = settings.media_url
AMQ_GUILD_ID: int = settings.amq_guild_id
PROMPTS_PATH: str = settings.prompts_path
