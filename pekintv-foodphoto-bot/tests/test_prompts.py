from __future__ import annotations

from pekintv_bot import prompts


def test_styles_registered() -> None:
    assert set(prompts.STYLES) == {"wood", "overhead", "backlight"}


def test_render_style_prompt_inserts_dish_name() -> None:
    rendered = prompts.render_style_prompt("wood", "焼き餓子")
    assert "焼き餓子" in rendered
    assert "ウォールナット" in rendered


def test_render_custom_style_prompt_contains_both() -> None:
    rendered = prompts.render_custom_style_prompt("鉄板から湯気が立つ瞬間", "焼き餓子")
    assert "焼き餓子" in rendered
    assert "鉄板から湯気が立つ瞬間" in rendered


def test_caption_prompt_contains_required_fields() -> None:
    rendered = prompts.render_caption_prompt("焼き餓子", "Pan-fried gyoza", "皮はパリッと")
    assert "焼き餓子" in rendered
    assert "Pan-fried gyoza" in rendered
    assert "皮はパリッと" in rendered
    assert "#餓子" in rendered
    assert "280 字以内" in rendered


def test_critique_prompt_specifies_n() -> None:
    rendered = prompts.render_critique_prompt("焼き餓子", n=3)
    assert "3 枚" in rendered
    assert "焼き餓子" in rendered
    assert "centered_score" in rendered
