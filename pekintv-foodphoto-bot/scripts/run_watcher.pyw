"""Entrypoint for Windows Task Scheduler (ONLOGON).

Run via pythonw.exe so no console window appears:
    pythonw.exe C:\\path\\to\\pekintv-foodphoto-bot\\scripts\\run_watcher.pyw

Logs go to %LOG_DIR%\\bot.log.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pekintv_bot.config import load_config
from pekintv_bot.gemini_client import GeminiClient
from pekintv_bot.logging_setup import setup_logging
from pekintv_bot.watcher import Watcher


def main() -> int:
    cfg = load_config()
    cfg.ensure_dirs()
    setup_logging(cfg.log_dir, stderr=False)

    client = GeminiClient(
        api_key=cfg.gemini_api_key,
        text_model=cfg.text_model,
        image_model=cfg.image_model,
        billing_mode=cfg.gemini_billing_mode,
        gcp_project_id=cfg.gcp_project_id,
        gcp_location=cfg.gcp_location,
    )
    Watcher(cfg, client).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
