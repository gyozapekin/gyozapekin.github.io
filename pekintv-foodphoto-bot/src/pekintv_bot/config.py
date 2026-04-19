"""Environment-backed configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    gemini_billing_mode: str
    gcp_project_id: str
    gcp_location: str

    box_watch_dir: Path
    draft_output_dir: Path
    approved_dir: Path
    rejected_dir: Path
    log_dir: Path

    text_model: str
    image_model: str
    max_variants: int
    free_tier_daily_limit: int
    stable_size_seconds: int
    retry_appetizing_threshold: int

    def ensure_dirs(self) -> None:
        for d in (self.draft_output_dir, self.approved_dir, self.rejected_dir, self.log_dir):
            d.mkdir(parents=True, exist_ok=True)


def _env_path(name: str, default: str | None = None) -> Path:
    raw = os.getenv(name, default)
    if not raw:
        raise RuntimeError(f"{name} is not set (.env or environment)")
    return Path(raw)


def load_config(env_file: str | Path | None = None) -> Config:
    if env_file:
        load_dotenv(env_file, override=True)
    else:
        load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Put it in .env.")

    return Config(
        gemini_api_key=api_key,
        gemini_billing_mode=os.getenv("GEMINI_BILLING_MODE", "ai_studio"),
        gcp_project_id=os.getenv("GCP_PROJECT_ID", ""),
        gcp_location=os.getenv("GCP_LOCATION", "us-central1"),
        box_watch_dir=_env_path("BOX_WATCH_DIR"),
        draft_output_dir=_env_path("DRAFT_OUTPUT_DIR"),
        approved_dir=_env_path("APPROVED_DIR"),
        rejected_dir=_env_path("REJECTED_DIR"),
        log_dir=_env_path("LOG_DIR"),
        text_model=os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash"),
        image_model=os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image"),
        max_variants=int(os.getenv("MAX_VARIANTS", "3")),
        free_tier_daily_limit=int(os.getenv("FREE_TIER_DAILY_LIMIT", "500")),
        stable_size_seconds=int(os.getenv("STABLE_SIZE_SECONDS", "3")),
        retry_appetizing_threshold=int(os.getenv("RETRY_APPETIZING_THRESHOLD", "7")),
    )
