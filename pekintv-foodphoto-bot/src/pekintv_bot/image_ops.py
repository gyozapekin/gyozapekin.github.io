"""Pillow helpers: EXIF rotation, platform resizes, centering heuristic."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pillow_heif  # type: ignore
    pillow_heif.register_heif_opener()
except ImportError:
    pass


INSTAGRAM_SIZE = (1080, 1350)
X_SIZE = (1600, 900)


def load_oriented(path: str | Path) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def resize_cover(img: Image.Image, target: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(img, target, method=Image.LANCZOS, centering=(0.5, 0.5))


def save_jpeg(img: Image.Image, path: str | Path, quality: int = 92) -> None:
    img.save(path, format="JPEG", quality=quality, optimize=True)


@dataclass
class CenteringResult:
    centered: bool
    center_brightness: float
    edge_brightness: float
    ratio: float


def is_subject_centered(img: Image.Image, tolerance: float = 0.15) -> CenteringResult:
    """Rough heuristic: split the image into a 3x3 grid and compare the center
    cell's saturation+brightness to the edge cells. A centered dish tends to
    have a higher-contrast / more-saturated center cell.

    Returns True when the center cell is at least (1 + tolerance) times brighter
    on average than the edge cells.
    """
    gray = img.convert("L")
    w, h = gray.size
    cw, ch = w // 3, h // 3

    def avg(box: tuple[int, int, int, int]) -> float:
        crop = gray.crop(box)
        hist = crop.getdata()
        return sum(hist) / max(len(hist), 1)

    center = avg((cw, ch, cw * 2, ch * 2))
    edges = [
        avg((0, 0, cw, ch)),
        avg((cw, 0, cw * 2, ch)),
        avg((cw * 2, 0, w, ch)),
        avg((0, ch, cw, ch * 2)),
        avg((cw * 2, ch, w, ch * 2)),
        avg((0, ch * 2, cw, h)),
        avg((cw, ch * 2, cw * 2, h)),
        avg((cw * 2, ch * 2, w, h)),
    ]
    edge_mean = sum(edges) / len(edges) if edges else 1.0
    ratio = center / max(edge_mean, 1e-6)
    return CenteringResult(
        centered=ratio >= (1.0 + tolerance),
        center_brightness=center,
        edge_brightness=edge_mean,
        ratio=ratio,
    )


def is_not_blank(img: Image.Image) -> bool:
    """Guard against pure-black or pure-white output from a failed generation."""
    gray = img.convert("L")
    pixels = list(gray.getdata())
    if not pixels:
        return False
    mean = sum(pixels) / len(pixels)
    return 10 < mean < 245
