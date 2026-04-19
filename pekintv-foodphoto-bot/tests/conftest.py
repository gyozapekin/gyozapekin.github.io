from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))


@pytest.fixture
def sample_jpeg_path(tmp_path: Path) -> Path:
    img = Image.new("RGB", (600, 450), (40, 30, 20))
    for x in range(200, 400):
        for y in range(150, 300):
            img.putpixel((x, y), (220, 180, 120))
    p = tmp_path / "sample.jpg"
    img.save(p, format="JPEG", quality=92)
    return p


@pytest.fixture
def fake_generated_bytes() -> bytes:
    img = Image.new("RGB", (1024, 1024), (180, 140, 90))
    for x in range(300, 724):
        for y in range(300, 724):
            img.putpixel((x, y), (240, 200, 140))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
