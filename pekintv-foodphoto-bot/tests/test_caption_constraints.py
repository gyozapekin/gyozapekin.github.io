from __future__ import annotations

from pekintv_bot.pipeline import _fallback_captions


def test_fallback_captions_have_required_hashtags() -> None:
    caps = _fallback_captions("焼き餓子")
    assert "#餓子" in caps["x"]
    assert "#北京" in caps["x"]
    assert "#大阪グルメ" in caps["x"]
    assert "#餓子" in caps["instagram"]


def test_fallback_x_caption_fits_280_chars() -> None:
    caps = _fallback_captions("焼き餓子")
    assert len(caps["x"]) <= 280
