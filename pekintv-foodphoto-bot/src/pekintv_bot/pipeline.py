"""End-to-end processing pipeline for a single source photo."""
from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from . import draft_writer, image_ops, prompts
from .config import Config
from .gemini_client import GeminiClient, bytes_to_pil


COST_IMAGE = 0.039
COST_TEXT = 0.003


def process(source: Path, cfg: Config, client: GeminiClient, custom_style: tuple[str, str] | None = None) -> Path:
    source = Path(source).resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    started = datetime.now()
    logger.info("Processing {}", source)

    try:
        original_img = image_ops.load_oriented(source)
    except Exception as exc:
        _record_error(cfg, source, f"load failed: {exc}")
        raise

    try:
        analysis = client.analyze_dish(source)
        logger.info("Analysis: {} ({})", analysis["dish_ja"], analysis["dish_slug"])
    except Exception as exc:
        _record_error(cfg, source, f"analyze failed: {exc}\n{traceback.format_exc()}")
        raise

    draft_dir = draft_writer.ensure_draft_dir(cfg.draft_output_dir, analysis["dish_slug"], now=started)
    draft_writer.save_original(original_img, draft_dir)

    style_keys = _resolve_styles(cfg, custom_style)
    variant_paths = _generate_variants(
        client=client,
        source=source,
        draft_dir=draft_dir,
        dish_ja=analysis["dish_ja"],
        style_keys=style_keys,
        custom_style=custom_style,
    )
    if not variant_paths:
        _record_error(cfg, source, "all variants failed")
        raise RuntimeError("All variant generations failed")

    try:
        critique = client.critique_variants(analysis["dish_ja"], variant_paths)
    except Exception as exc:
        logger.warning("Critique failed, proceeding without scores: {}", exc)
        critique = _empty_critique(variant_paths)

    retry_info: dict[str, Any] | None = None
    best_entry = _best_entry(critique)
    threshold = cfg.retry_appetizing_threshold
    alt_prompt = (critique or {}).get("suggested_alternative_prompt")
    best_score = (best_entry or {}).get("appetizing_score")
    if best_entry and isinstance(best_score, (int, float)) and best_score < threshold and alt_prompt:
        logger.info("Best appetizing_score={} < {}; retrying with alt prompt", best_entry.get("appetizing_score"), threshold)
        retry_path = _generate_retry(client, source, draft_dir, analysis["dish_ja"], alt_prompt)
        if retry_path:
            retry_info = {"file": retry_path.name, "prompt": alt_prompt}
            try:
                critique = client.critique_variants(analysis["dish_ja"], variant_paths + [retry_path])
            except Exception as exc:
                logger.warning("Re-critique after retry failed: {}", exc)

    draft_writer.save_critique(draft_dir, critique)

    try:
        captions = client.write_caption(
            dish_ja=analysis["dish_ja"],
            dish_en=analysis["dish_en"],
            notes=analysis.get("notes", ""),
        )
    except Exception as exc:
        logger.warning("Caption generation failed: {}", exc)
        captions = _fallback_captions(analysis["dish_ja"])

    draft_writer.save_captions(draft_dir, captions)

    text_calls = 3 + (1 if retry_info else 0)
    image_calls = len(variant_paths) + (1 if retry_info else 0)
    metadata = {
        "source": str(source),
        "processed_at": started.isoformat(timespec="seconds"),
        "analysis": analysis,
        "styles": style_keys,
        "variants": [p.name for p in variant_paths],
        "retry": retry_info,
        "models": {"text": cfg.text_model, "image": cfg.image_model},
        "estimated_cost_usd": round(text_calls * COST_TEXT + image_calls * COST_IMAGE, 4),
        "billing_mode": cfg.gemini_billing_mode,
    }
    draft_writer.save_metadata(draft_dir, metadata)
    logger.info("Draft ready: {}", draft_dir)
    return draft_dir


def _resolve_styles(cfg: Config, custom_style: tuple[str, str] | None) -> list[str]:
    if custom_style:
        return [custom_style[0]]
    order = ["wood", "overhead", "backlight"]
    return order[: cfg.max_variants]


def _generate_variants(
    *,
    client: GeminiClient,
    source: Path,
    draft_dir: Path,
    dish_ja: str,
    style_keys: list[str],
    custom_style: tuple[str, str] | None,
) -> list[Path]:
    def _one(style_key: str) -> Path | None:
        try:
            if custom_style and style_key == custom_style[0]:
                prompt_text = prompts.render_custom_style_prompt(custom_style[1], dish_ja)
                filename = f"variant_{custom_style[0]}.jpg"
            else:
                prompt_text = prompts.render_style_prompt(style_key, dish_ja)
                filename = prompts.STYLES[style_key].filename
            data = client.enhance_image(source, prompt_text)
            img = bytes_to_pil(data)
            if not image_ops.is_not_blank(img):
                logger.warning("Variant {} came back blank, skipping", style_key)
                return None
            return draft_writer.save_variant(img, draft_dir, filename)
        except Exception as exc:
            logger.warning("Variant {} failed: {}", style_key, exc)
            return None

    results: list[Path] = []
    with ThreadPoolExecutor(max_workers=max(1, len(style_keys))) as pool:
        for path in pool.map(_one, style_keys):
            if path is not None:
                results.append(path)
    return results


def _generate_retry(client: GeminiClient, source: Path, draft_dir: Path, dish_ja: str, alt_prompt: str) -> Path | None:
    try:
        full_prompt = prompts.render_custom_style_prompt(alt_prompt, dish_ja)
        data = client.enhance_image(source, full_prompt)
        img = bytes_to_pil(data)
        if not image_ops.is_not_blank(img):
            return None
        return draft_writer.save_variant(img, draft_dir, "variant_retry.jpg")
    except Exception as exc:
        logger.warning("Retry variant failed: {}", exc)
        return None


def _empty_critique(variant_paths: list[Path]) -> dict[str, Any]:
    return {
        "variants": [
            {
                "file": p.name,
                "centered_score": None,
                "appetizing_score": None,
                "composition_score": None,
                "brand_fit_score": None,
                "issues": ["critique unavailable"],
                "strengths": [],
            }
            for p in variant_paths
        ],
        "best_variant_file": variant_paths[0].name if variant_paths else None,
        "suggested_alternative_prompt": None,
        "overall_verdict": "手動確認推奨",
    }


def _best_entry(critique: dict[str, Any]) -> dict[str, Any] | None:
    variants = critique.get("variants") or []
    best_file = critique.get("best_variant_file")
    if best_file:
        for v in variants:
            if v.get("file") == best_file:
                return v
    if variants:
        return max(variants, key=lambda v: v.get("appetizing_score") or 0)
    return None


def _fallback_captions(dish_ja: str) -> dict[str, str]:
    return {
        "x": f"【本日のおすすめ】{dish_ja} 🥟\n#餓子 #北京 #大阪グルメ",
        "instagram": (
            f"本日のおすすめ: {dish_ja} 🥟\n\n"
            "ぜひお店でお楽しみください。\n\n"
            "#餓子 #北京 #大阪グルメ #osakafood #gyoza"
        ),
    }


def _record_error(cfg: Config, source: Path, message: str) -> None:
    try:
        cfg.rejected_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        err_dir = cfg.rejected_dir / f"{stamp}_error"
        err_dir.mkdir(parents=True, exist_ok=True)
        (err_dir / "error.log").write_text(message, encoding="utf-8")
        try:
            img = image_ops.load_oriented(source)
            image_ops.save_jpeg(img, err_dir / "original.jpg")
        except Exception:
            pass
    except Exception as exc:
        logger.error("Could not record error directory: {}", exc)
