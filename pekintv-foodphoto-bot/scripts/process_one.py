"""Manual single-photo entrypoint. Usage:

    python scripts/process_one.py path/to/photo.jpg
    python scripts/process_one.py path/to/photo.jpg --style wood
    python scripts/process_one.py path/to/photo.jpg --style custom "鉄板から湯気が立つ瞬間"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pekintv_bot.config import load_config  # noqa: E402
from pekintv_bot.gemini_client import GeminiClient  # noqa: E402
from pekintv_bot.logging_setup import setup_logging  # noqa: E402
from pekintv_bot.pipeline import process  # noqa: E402


_ALT_EXTS = [".jpg", ".jpeg", ".JPG", ".JPEG", ".png", ".PNG", ".heic", ".HEIC", ".webp", ".WEBP"]


def resolve_image_path(p: Path) -> Path:
    if p.exists():
        return p
    base = p.with_suffix("")
    for ext in _ALT_EXTS:
        candidate = base.with_suffix(ext)
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Image not found: {p} (also tried {_ALT_EXTS})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--style", nargs="+", default=None,
                        help="Force one style: wood | overhead | backlight | custom <prompt>")
    args = parser.parse_args(argv)

    args.image = resolve_image_path(args.image)
    cfg = load_config()
    cfg.ensure_dirs()
    setup_logging(cfg.log_dir)

    client = GeminiClient(
        api_key=cfg.gemini_api_key,
        text_model=cfg.text_model,
        image_model=cfg.image_model,
        billing_mode=cfg.gemini_billing_mode,
        gcp_project_id=cfg.gcp_project_id,
        gcp_location=cfg.gcp_location,
    )

    custom_style: tuple[str, str] | None = None
    if args.style:
        if args.style[0] == "custom":
            if len(args.style) < 2:
                parser.error("--style custom requires a prompt text")
            custom_style = ("custom", " ".join(args.style[1:]))
        elif args.style[0] in {"wood", "overhead", "backlight"}:
            custom_style = (args.style[0], "")
        else:
            parser.error(f"unknown style {args.style[0]!r}")

    if custom_style and custom_style[0] != "custom" and not custom_style[1]:
        from pekintv_bot.prompts import STYLES
        custom_style = (custom_style[0], STYLES[custom_style[0]].prompt_template)

    draft = process(args.image, cfg, client, custom_style=custom_style)
    print(str(draft))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
