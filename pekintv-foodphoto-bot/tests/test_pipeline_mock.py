"""End-to-end pipeline test with a fake Gemini client — no network calls."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pekintv_bot import pipeline
from pekintv_bot.config import Config


class FakeClient:
    def __init__(self, image_bytes: bytes, fail_critique: bool = False, low_appetizing: bool = False) -> None:
        self.image_bytes = image_bytes
        self.enhance_calls: list[str] = []
        self.fail_critique = fail_critique
        self.low_appetizing = low_appetizing

    def analyze_dish(self, image_path):  # noqa: ANN001
        return {
            "dish_ja": "焼き餓子",
            "dish_en": "Pan-fried gyoza",
            "dish_slug": "yaki-gyoza",
            "item_count": 6,
            "lighting_score": 4,
            "composition_score": 3,
            "clutter": "low",
            "notes": "皮はパリッと焼き上げ",
        }

    def enhance_image(self, image_path, style_prompt):  # noqa: ANN001
        self.enhance_calls.append(style_prompt)
        return self.image_bytes

    def critique_variants(self, dish_ja: str, variant_files: list[Path]):
        if self.fail_critique:
            raise RuntimeError("boom")
        score = 5 if self.low_appetizing else 8
        return {
            "variants": [
                {
                    "file": p.name,
                    "centered_score": 8,
                    "appetizing_score": score,
                    "composition_score": 7,
                    "brand_fit_score": 8,
                    "strengths": ["明るい"],
                    "issues": [],
                }
                for p in variant_files
            ],
            "best_variant_file": variant_files[0].name,
            "overall_verdict": "採用推奨" if not self.low_appetizing else "再生成推奨",
            "suggested_alternative_prompt": "鉄板から湯気が立ちのぼる瞬間",
        }

    def write_caption(self, *, dish_ja: str, dish_en: str, notes: str):
        return {
            "x": f"本日のおすすめ: {dish_ja} 🥟 #餓子 #北京 #大阪グルメ",
            "instagram": f"本日のおすすめ: {dish_ja} 🥟\n\n#餓子 #北京 #大阪グルメ #osakafood",
        }


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    return Config(
        gemini_api_key="test",
        gemini_billing_mode="ai_studio",
        gcp_project_id="",
        gcp_location="us-central1",
        box_watch_dir=tmp_path / "originals",
        draft_output_dir=tmp_path / "drafts",
        approved_dir=tmp_path / "approved",
        rejected_dir=tmp_path / "rejected",
        log_dir=tmp_path / "logs",
        text_model="gemini-2.5-flash",
        image_model="gemini-2.5-flash-image",
        max_variants=3,
        free_tier_daily_limit=500,
        stable_size_seconds=1,
        retry_appetizing_threshold=7,
    )


def test_process_full_pipeline(cfg: Config, sample_jpeg_path: Path, fake_generated_bytes: bytes) -> None:
    cfg.ensure_dirs()
    client = FakeClient(fake_generated_bytes)
    draft = pipeline.process(sample_jpeg_path, cfg, client)

    assert draft.exists()
    assert (draft / "original.jpg").exists()
    assert (draft / "variant_wood_table.jpg").exists()
    assert (draft / "variant_overhead.jpg").exists()
    assert (draft / "variant_backlight.jpg").exists()
    assert (draft / "ig_variant_wood_table.jpg").exists()
    assert (draft / "x_variant_wood_table.jpg").exists()
    assert (draft / "caption_x.txt").read_text(encoding="utf-8").startswith("本日のおすすめ")
    assert (draft / "caption_instagram.txt").exists()
    assert (draft / "critique.json").exists()
    assert (draft / "critique.md").exists()

    meta = json.loads((draft / "metadata.json").read_text(encoding="utf-8"))
    assert meta["analysis"]["dish_ja"] == "焼き餓子"
    assert meta["styles"] == ["wood", "overhead", "backlight"]
    assert len(meta["variants"]) == 3
    assert meta["retry"] is None
    assert meta["estimated_cost_usd"] > 0


def test_process_triggers_retry_on_low_score(cfg: Config, sample_jpeg_path: Path, fake_generated_bytes: bytes) -> None:
    cfg.ensure_dirs()
    client = FakeClient(fake_generated_bytes, low_appetizing=True)
    draft = pipeline.process(sample_jpeg_path, cfg, client)

    assert (draft / "variant_retry.jpg").exists()
    meta = json.loads((draft / "metadata.json").read_text(encoding="utf-8"))
    assert meta["retry"] is not None
    assert meta["retry"]["file"] == "variant_retry.jpg"


def test_process_survives_critique_failure(cfg: Config, sample_jpeg_path: Path, fake_generated_bytes: bytes) -> None:
    cfg.ensure_dirs()
    client = FakeClient(fake_generated_bytes, fail_critique=True)
    draft = pipeline.process(sample_jpeg_path, cfg, client)

    assert (draft / "caption_x.txt").exists()
    critique = json.loads((draft / "critique.json").read_text(encoding="utf-8"))
    assert critique["overall_verdict"] == "手動確認推奨"


def test_process_custom_style(cfg: Config, sample_jpeg_path: Path, fake_generated_bytes: bytes) -> None:
    cfg.ensure_dirs()
    client = FakeClient(fake_generated_bytes)
    draft = pipeline.process(
        sample_jpeg_path, cfg, client, custom_style=("custom", "暗めの背景に主役をくっきり")
    )
    assert (draft / "variant_custom.jpg").exists()
    assert len(client.enhance_calls) == 1
    assert "暗めの背景" in client.enhance_calls[0]
