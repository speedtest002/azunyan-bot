from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import warnings

import pytz


def setup_logging() -> logging.Logger:
    # Ẩn các DeprecationWarning không cần thiết từ thư viện bên thứ 3
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.genai")
    
    logger = logging.getLogger("azunyan")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}",
        "%Y-%m-%d %H:%M:%S",
        style="{",
    )

    # UTC+7 timezone
    def tz_converter(*args):
        return datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).timetuple()

    formatter.converter = tz_converter

    from core.config import settings
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "azunyan.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    # Logger commands
    cmd_logger = logging.getLogger("azunyan.cmd")
    cmd_logger.setLevel(logging.INFO)
    cmd_logger.addHandler(file_handler)
    cmd_logger.addHandler(console_handler)
    cmd_logger.propagate = False

    return logger