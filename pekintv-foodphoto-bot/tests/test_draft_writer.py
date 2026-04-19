from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PIL import Image

from pekintv_bot import draft_writer


def test_build_draft_folder_name() -> None:
    when = datetime(2026, 4, 19, 18, 30)
    assert draft_writer.build_draft_folder_name("yaki-gyoza", when) == "20260419_1830_yaki-gyoza"


def test_save_variant_writes_base_ig_x(tmp_path: Path) -> None:
    img = Image.new("RGB", (1200, 1200), (180, 120, 80))
    draft_dir = draft_writer.ensure_draft_dir(tmp_path, "gyoza", now=datetime(2026, 4, 19, 18, 30))
    draft_writer.save_variant(img, draft_dir, "variant_wood_table.jpg")
    assert (draft_dir / "variant_wood_table.jpg").exists()
    assert (draft_dir / "ig_variant_wood_table.jpg").exists()
    assert (draft_dir / "x_variant_wood_table.jpg").exists()


def test_save_captions_utf8(tmp_path: Path) -> None:
    draft_dir = draft_writer.ensure_draft_dir(tmp_path, "gyoza")
    draft_writer.save_captions(
        draft_dir,
        {"x": "焼き餓子🥟 #餓子 #北京 #大阪グルメ", "instagram": "本日のおすすめ🥟\n#餓子"},
    )
    assert (draft_dir / "caption_x.txt").read_text(encoding="utf-8").startswith("焼き餓子")
    assert "本日のおすすめ" in (draft_dir / "caption_instagram.txt").read_text(encoding="utf-8")


def test_save_metadata_serializes_json(tmp_path: Path) -> None:
    draft_dir = draft_writer.ensure_draft_dir(tmp_path, "gyoza")
    draft_writer.save_metadata(draft_dir, {"dish": "焼き餓子", "cost": 0.13, "variants": ["a.jpg"]})
    data = json.loads((draft_dir / "metadata.json").read_text(encoding="utf-8"))
    assert data["dish"] == "焼き餓子"
    assert data["cost"] == 0.13


def test_critique_md_includes_scores(tmp_path: Path) -> None:
    draft_dir = draft_writer.ensure_draft_dir(tmp_path, "gyoza")
    draft_writer.save_critique(
        draft_dir,
        {
            "variants": [
                {
                    "file": "variant_wood_table.jpg",
                    "centered_score": 8,
                    "appetizing_score": 7,
                    "composition_score": 8,
                    "brand_fit_score": 9,
                    "strengths": ["木目が温かい"],
                    "issues": ["背景がやや暗い"],
                }
            ],
            "best_variant_file": "variant_wood_table.jpg",
            "overall_verdict": "採用推奨",
            "suggested_alternative_prompt": "湯気を立ててみる",
        },
    )
    md = (draft_dir / "critique.md").read_text(encoding="utf-8")
    assert "variant_wood_table.jpg" in md
    assert "8 / 10" in md
    assert "採用推奨" in md
    assert "湯気を立ててみる" in md
