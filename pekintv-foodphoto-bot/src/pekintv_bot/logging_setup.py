"""Loguru configuration with daily-rotated log file."""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_dir: Path, stderr: bool = True) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    if stderr:
        logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level: <7} | {message}")
    logger.add(
        log_dir / "bot.log",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        level="DEBUG",
        enqueue=True,
    )
