"""Thin wrapper over google-genai SDK for the four call types we need.

All methods are synchronous; callers can parallelize at the pipeline level
with threads. The client is designed to be mockable in tests — the pipeline
only ever calls the public methods, never uses the underlying SDK directly.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from loguru import logger
from PIL import Image

from . import prompts


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        text_model: str,
        image_model: str,
        billing_mode: str = "ai_studio",
        gcp_project_id: str = "",
        gcp_location: str = "us-central1",
    ) -> None:
        from google import genai  # local import so tests can mock cleanly

        if billing_mode == "vertex":
            if not gcp_project_id:
                raise RuntimeError("GCP_PROJECT_ID is required when GEMINI_BILLING_MODE=vertex.")
            self._client = genai.Client(vertexai=True, project=gcp_project_id, location=gcp_location)
        else:
            self._client = genai.Client(api_key=api_key)
        self.text_model = text_model
        self.image_model = image_model

    def analyze_dish(self, image_path: Path) -> dict[str, Any]:
        img = _load_image_bytes(image_path)
        resp = self._generate_json(
            model=self.text_model,
            contents=[img, prompts.ANALYZE_PROMPT],
        )
        logger.debug("analyze_dish → {}", resp)
        return _coerce_analyze(resp)

    def critique_variants(
        self,
        dish_ja: str,
        variant_files: list[Path],
    ) -> dict[str, Any]:
        parts: list[Any] = [prompts.render_critique_prompt(dish_ja=dish_ja, n=len(variant_files))]
        for p in variant_files:
            parts.append(_load_image_bytes(p))
            parts.append(f"↑ ファイル名: {p.name}")
        resp = self._generate_json(model=self.text_model, contents=parts)
        logger.debug("critique → best={} verdict={}", resp.get("best_variant_file"), resp.get("overall_verdict"))
        return resp

    def write_caption(self, dish_ja: str, dish_en: str, notes: str) -> dict[str, str]:
        prompt = prompts.render_caption_prompt(dish_ja=dish_ja, dish_en=dish_en, notes=notes)
        resp = self._generate_json(model=self.text_model, contents=[prompt])
        return {"x": str(resp.get("x", "")), "instagram": str(resp.get("instagram", ""))}

    def enhance_image(self, image_path: Path, style_prompt: str) -> bytes:
        from google.genai import types

        img_part = _load_image_bytes(image_path)
        response = self._client.models.generate_content(
            model=self.image_model,
            contents=[img_part, style_prompt],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        return _extract_first_image_bytes(response)

    def _generate_json(self, model: str, contents: list[Any]) -> dict[str, Any]:
        from google.genai import types

        response = self._client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        text = getattr(response, "text", "") or ""
        if not text:
            try:
                text = response.candidates[0].content.parts[0].text  # type: ignore[attr-defined]
            except Exception:
                pass
        text = text.strip()
        if not text:
            raise RuntimeError("Gemini returned empty text response")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Gemini JSON: {!r}", text[:500])
            raise RuntimeError(f"Gemini did not return valid JSON: {exc}") from exc


def _load_image_bytes(path: Path) -> Any:
    try:
        from google.genai import types

        data = Path(path).read_bytes()
        mime = _guess_mime(path)
        return types.Part.from_bytes(data=data, mime_type=mime)
    except Exception:
        return Image.open(path)


def _guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".heic": "image/heic",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")


def _extract_first_image_bytes(response: Any) -> bytes:
    try:
        candidates = response.candidates  # type: ignore[attr-defined]
    except Exception as exc:
        raise RuntimeError(f"Unexpected Gemini response shape: {exc}") from exc

    for cand in candidates or []:
        parts = getattr(getattr(cand, "content", None), "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                data = inline.data
                if isinstance(data, str):
                    import base64

                    data = base64.b64decode(data)
                return data
    raise RuntimeError("Gemini image response contained no inline image data")


def _coerce_analyze(resp: dict[str, Any]) -> dict[str, Any]:
    out = {
        "dish_ja": str(resp.get("dish_ja") or "料理"),
        "dish_en": str(resp.get("dish_en") or "Dish"),
        "dish_slug": _sanitize_slug(str(resp.get("dish_slug") or resp.get("dish_en") or "dish")),
        "item_count": int(resp.get("item_count") or 1),
        "lighting_score": int(resp.get("lighting_score") or 3),
        "composition_score": int(resp.get("composition_score") or 3),
        "clutter": str(resp.get("clutter") or "low"),
        "notes": str(resp.get("notes") or ""),
    }
    return out


def _sanitize_slug(raw: str) -> str:
    import re

    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "dish"


def bytes_to_pil(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")
