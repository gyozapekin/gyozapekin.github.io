"""Create `03_drafts/<timestamp>_<slug>/` folders with variants, captions, and metadata."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from . import image_ops


def build_draft_folder_name(dish_slug: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"{now.strftime('%Y%m%d_%H%M')}_{dish_slug}"


def ensure_draft_dir(root: Path, dish_slug: str, now: datetime | None = None) -> Path:
    folder = root / build_draft_folder_name(dish_slug, now)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_original(img: Image.Image, draft_dir: Path) -> Path:
    path = draft_dir / "original.jpg"
    image_ops.save_jpeg(img, path)
    return path


def save_variant(img: Image.Image, draft_dir: Path, filename: str) -> Path:
    """Save both IG (1080x1350) and X (1600x900) crops alongside the base."""
    base_path = draft_dir / filename
    ig_path = draft_dir / f"ig_{filename}"
    x_path = draft_dir / f"x_{filename}"
    image_ops.save_jpeg(img, base_path)
    image_ops.save_jpeg(image_ops.resize_cover(img, image_ops.INSTAGRAM_SIZE), ig_path)
    image_ops.save_jpeg(image_ops.resize_cover(img, image_ops.X_SIZE), x_path)
    return base_path


def save_captions(draft_dir: Path, captions: dict[str, str]) -> None:
    (draft_dir / "caption_x.txt").write_text(captions.get("x", ""), encoding="utf-8")
    (draft_dir / "caption_instagram.txt").write_text(captions.get("instagram", ""), encoding="utf-8")


def save_critique(draft_dir: Path, critique: dict[str, Any]) -> None:
    (draft_dir / "critique.json").write_text(
        json.dumps(critique, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (draft_dir / "critique.md").write_text(_render_critique_md(critique), encoding="utf-8")


def save_metadata(draft_dir: Path, metadata: dict[str, Any]) -> None:
    (draft_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _render_critique_md(critique: dict[str, Any]) -> str:
    lines: list[str] = ["# バリアント評価", ""]
    variants = critique.get("variants") or []
    for v in variants:
        lines.append(f"## {v.get('file', '?')}")
        lines.append(
            f"- 中央配置: {v.get('centered_score', '-')} / 10  \n"
            f"- おいしそう: {v.get('appetizing_score', '-')} / 10  \n"
            f"- 構図: {v.get('composition_score', '-')} / 10  \n"
            f"- ブランド適合: {v.get('brand_fit_score', '-')} / 10"
        )
        strengths = v.get("strengths") or []
        if strengths:
            lines.append("- 良い点: " + " / ".join(str(s) for s in strengths))
        issues = v.get("issues") or []
        if issues:
            lines.append("- 気になる点: " + " / ".join(str(s) for s in issues))
        lines.append("")
    lines.append(f"**推奨**: `{critique.get('best_variant_file', '?')}`")
    lines.append(f"**総評**: {critique.get('overall_verdict', '-')}")
    alt = critique.get("suggested_alternative_prompt")
    if alt:
        lines.append("")
        lines.append(f"**もっと映える代替案プロンプト**:\n> {alt}")
    return "\n".join(lines) + "\n"
