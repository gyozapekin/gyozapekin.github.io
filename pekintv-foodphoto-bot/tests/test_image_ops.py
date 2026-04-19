from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from pekintv_bot import image_ops


def test_load_oriented_converts_to_rgb(sample_jpeg_path: Path) -> None:
    img = image_ops.load_oriented(sample_jpeg_path)
    assert img.mode == "RGB"
    assert img.size == (600, 450)


def test_resize_cover_matches_target() -> None:
    img = Image.new("RGB", (2000, 1000), (255, 255, 255))
    ig = image_ops.resize_cover(img, image_ops.INSTAGRAM_SIZE)
    x = image_ops.resize_cover(img, image_ops.X_SIZE)
    assert ig.size == image_ops.INSTAGRAM_SIZE == (1080, 1350)
    assert x.size == image_ops.X_SIZE == (1600, 900)


def test_is_subject_centered_on_brighter_center(sample_jpeg_path: Path) -> None:
    img = image_ops.load_oriented(sample_jpeg_path)
    result = image_ops.is_subject_centered(img, tolerance=0.1)
    assert result.centered
    assert result.ratio > 1.0


def test_is_not_blank_detects_white_and_black() -> None:
    black = Image.new("RGB", (100, 100), (0, 0, 0))
    white = Image.new("RGB", (100, 100), (255, 255, 255))
    mid = Image.new("RGB", (100, 100), (120, 100, 80))
    assert not image_ops.is_not_blank(black)
    assert not image_ops.is_not_blank(white)
    assert image_ops.is_not_blank(mid)


def test_save_jpeg_roundtrip(tmp_path: Path) -> None:
    img = Image.new("RGB", (64, 64), (200, 100, 50))
    out = tmp_path / "out.jpg"
    image_ops.save_jpeg(img, out, quality=90)
    assert out.exists() and out.stat().st_size > 0
    loaded = Image.open(out)
    assert loaded.size == (64, 64)
