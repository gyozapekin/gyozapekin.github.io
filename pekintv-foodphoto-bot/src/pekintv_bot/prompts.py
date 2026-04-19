"""Prompt templates for Gemini calls.

All prompts are tuned for 餓子専門店「北京」 (Osaka gyoza restaurant).
Edit the constants here to re-tune tone and visual style without touching the
rest of the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass


ANALYZE_PROMPT = """\
あなたは日本の飲食店のフードフォト監修者です。
添付の写真を見て、以下のフィールドを持つ JSON を返してください。
余計な文字は一切付けず、JSON のみ返してください。

{
  "dish_ja": "料理名（日本語、なるべく具体的に）",
  "dish_en": "Dish name in English",
  "dish_slug": "ローマ字スラグ（小文字・ハイフン区切り、例: yaki-gyoza）",
  "item_count": 数量（皿数・個数の推定、不明なら1）,
  "lighting_score": 1-5の整数（1=暗く濁る / 5=自然光でクリア）,
  "composition_score": 1-5の整数,
  "clutter": "背景の雑多さ（none/low/medium/high）",
  "notes": "改善のヒント（1-2文、日本語）"
}
"""


@dataclass(frozen=True)
class StylePrompt:
    key: str
    filename: str
    prompt_template: str


STYLE_WOOD_TABLE = StylePrompt(
    key="wood",
    filename="variant_wood_table.jpg",
    prompt_template=(
        "この料理（{dish_ja}）の写真を編集してください。"
        "温かみのあるウォールナット木目テーブルの上に自然に配置し、"
        "左斜め前からの柔らかな自然光、浅い被写界深度、"
        "背景はわずかにボケたレストラン内装。"
        "料理本体は元画像の色味・質感・形状を忠実に保ち、"
        "フレーム中央やや下寄りに大きく配置してください。"
        "フォトリアルで、SNS（Instagram）映えする仕上がりに。"
    ),
)

STYLE_OVERHEAD = StylePrompt(
    key="overhead",
    filename="variant_overhead.jpg",
    prompt_template=(
        "この料理（{dish_ja}）の写真を真上から撮った俯瞰フラットレイに編集してください。"
        "背景はダークスレートまたは黒い和風テーブル、"
        "箸・小皿・薬味などの小物を添えてエディトリアル・フードフォト風に。"
        "料理は画面中央、やや明度高めで、彩度はリッチに。"
        "元の料理の見た目を忠実に保ち、追加・削除はしないでください。"
    ),
)

STYLE_BACKLIGHT = StylePrompt(
    key="backlight",
    filename="variant_backlight.jpg",
    prompt_template=(
        "この料理（{dish_ja}）を切り抜き、"
        "湯気が立ちのぼる厨房の背景に配置した逆光シーンに編集してください。"
        "料理の輪郭にゴールドアワーの柔らかな逆光、"
        "立ちのぼる湯気は控えめに（過剰にしない）、"
        "背景はふんわりボケた暖色トーン。"
        "料理本体の形状・色味・トッピングは元画像に忠実に保ってください。"
    ),
)

STYLES: dict[str, StylePrompt] = {
    STYLE_WOOD_TABLE.key: STYLE_WOOD_TABLE,
    STYLE_OVERHEAD.key: STYLE_OVERHEAD,
    STYLE_BACKLIGHT.key: STYLE_BACKLIGHT,
}


def render_style_prompt(style_key: str, dish_ja: str) -> str:
    style = STYLES[style_key]
    return style.prompt_template.format(dish_ja=dish_ja)


def render_custom_style_prompt(custom_prompt: str, dish_ja: str) -> str:
    return (
        f"この料理（{dish_ja}）を編集してください。料理本体の色味・形状・具材は元画像に忠実に保ったまま、"
        f"以下の指示に従ってください: {custom_prompt}"
    )


CRITIQUE_PROMPT = """\
あなたは日本のフードフォト編集者です。
これから {n} 枚の「加工済み料理写真」を順番に受け取ります。
これらは元画像（{dish_ja}）を異なるスタイルで加工したものです。
各写真を 4 観点で 0–10 で採点し、最も SNS で映えるものを選んでください。
出力は JSON のみ、余計な文字は付けないでください。

観点:
- centered_score: 料理が画面の中央に収まっているか
- appetizing_score: 見ていておいしそうに感じるか（ライティング・色味・質感）
- composition_score: 構図・余白・小物のバランス
- brand_fit_score: 大阪の餓子・中華料理店（親しみやすく、家族的、庶民派）の世界観に合うか

スキーマ:
{{
  "variants": [
    {{
      "index": 0,
      "file": "variant_xxx.jpg",
      "centered_score": 0-10,
      "appetizing_score": 0-10,
      "composition_score": 0-10,
      "brand_fit_score": 0-10,
      "issues": ["短い指摡00001", "短い指摡00002"],
      "strengths": ["短い評価00001"]
    }}
  ],
  "best_variant_index": 0,
  "best_variant_file": "variant_xxx.jpg",
  "suggested_alternative_prompt": "もっと映える代替案を日本語で1-2文（次の加工で使えるプロンプト形式）。例: 鉄板から湯気が立つ瞬間、暗めの背景に主役をくっきり。",
  "overall_verdict": "採用推奨 | 再生成推奨"
}}
"""


CAPTION_PROMPT = """\
あなたは大阪の餓子専門店「北京（ペキン）」の SNS 担当ライターです。
以下の料理の写真について、X（Twitter）用と Instagram 用のキャプションを日本語で作成してください。

料理情報:
- 料理名: {dish_ja} ({dish_en})
- 特徴メモ: {notes}

スタイル指針:
- 親しみやすく、大阪らしい温かさ。
- 過剰表現（「絶品」「日本一」「世界一」等）は避ける。
- 絵文字は適度に。料理写真を魅力的に伝える自然な文章。
- 店舗情報や営業時間は書かない（別で掲載されるため）。

出力は JSON のみ:
{{
  "x": "X（Twitter）用キャプション。280 字以内。ハッシュタグは #餓子 #北京 #大阪グルメ を必ず含め、合計2-3個。",
  "instagram": "Instagram 用キャプション。3-5段落、絵文字を適度に使用。本文末尾にハッシュタグブロック（15-20個、#餓子 #北京 #大阪グルメ #osakafood #gyoza などを含む）。"
}}
"""


def render_caption_prompt(dish_ja: str, dish_en: str, notes: str) -> str:
    return CAPTION_PROMPT.format(dish_ja=dish_ja, dish_en=dish_en, notes=notes or "（なし）")


def render_critique_prompt(dish_ja: str, n: int) -> str:
    return CRITIQUE_PROMPT.format(dish_ja=dish_ja, n=n)
