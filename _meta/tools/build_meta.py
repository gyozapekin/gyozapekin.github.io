#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海鮮餃子 北京 メタ情報ビルダー(Phase 0)

data/ の JSON を正本として、以下を生成する。
  dist/jsonld/*.html   各ページに貼り付ける <script type="application/ld+json"> ブロック
  dist/faq_section.html  ページに表示するFAQのHTML(構造化データと表示内容を一致させるため)
  dist/llms.txt          生成AIクローラ向けのサイト要約
  dist/llms-full.txt     営業情報とメニュー全文
  dist/robots_append.txt robots.txt に追記するAIクローラ許可の記述

使い方:
    python3 tools/build_meta.py
    python3 tools/build_meta.py --out dist
"""

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

WD_JA = {
    "Monday": "月曜日", "Tuesday": "火曜日", "Wednesday": "水曜日",
    "Thursday": "木曜日", "Friday": "金曜日", "Saturday": "土曜日",
    "Sunday": "日曜日",
}


def yen(n):
    """3桁区切りの金額表記にする(読み手が人でもAIでも読みやすい形)。"""
    return "{:,}".format(n)


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def strip_comments(obj):
    """_comment や _todo で始まるキーを再帰的に除去する(生成物には出さない)。"""
    if isinstance(obj, dict):
        return {k: strip_comments(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [strip_comments(v) for v in obj]
    return obj


def jsonld_block(payload):
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return '<script type="application/ld+json">\n%s\n</script>\n' % body


# ---------------------------------------------------------------- Restaurant


def build_restaurant(shop):
    site = shop["url"].rstrip("/")
    addr = shop["address"]
    hours = shop["hours"]

    node = {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "@id": site + "/#restaurant",
        "name": shop["name"],
        "alternateName": shop["nameEn"],
        "description": shop["description"],
        "url": shop["url"],
        "telephone": shop["telephone"],
        "faxNumber": shop.get("faxNumber"),
        "email": shop.get("email"),
        "image": shop.get("image", []),
        "priceRange": shop["priceRange"],
        "currenciesAccepted": shop.get("currenciesAccepted", "JPY"),
        "paymentAccepted": ", ".join(shop.get("paymentAccepted", [])),
        "servesCuisine": shop.get("servesCuisine", []),
        "address": {
            "@type": "PostalAddress",
            "postalCode": addr["postalCode"],
            "addressCountry": addr["addressCountry"],
            "addressRegion": addr["addressRegion"],
            "addressLocality": addr["addressLocality"],
            "streetAddress": addr["streetAddress"],
        },
        "hasMap": "https://maps.google.com/maps?q=%s+%s%s%s" % (
            shop["name"], addr["addressRegion"], addr["addressLocality"], addr["streetAddress"]
        ),
        "openingHoursSpecification": [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["https://schema.org/" + d for d in hours["openDays"]],
                "opens": hours["open"],
                "closes": hours["close"],
            }
        ],
        "hasMenu": shop["keyPages"]["menu"],
        "acceptsReservations": shop["features"]["acceptsReservations"],
        "publicAccess": True,
        "isAccessibleForFree": False,
        "sameAs": shop.get("sameAs", []),
        "amenityFeature": [],
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "定休日", "value": hours["closedLabel"]},
            {"@type": "PropertyValue", "name": "ラストオーダー", "value": hours["lastOrder"]},
            {"@type": "PropertyValue", "name": "アクセス", "value": " / ".join(shop.get("access", []))},
        ],
    }

    geo = shop.get("geo") or {}
    if geo.get("latitude") is not None and geo.get("longitude") is not None:
        node["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
        }

    # 休業日は closes と opens を同じ値にして「その曜日は営業しない」ことを明示する
    for d in hours.get("closedDays", []):
        node["openingHoursSpecification"].append({
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": "https://schema.org/" + d,
            "opens": "00:00",
            "closes": "00:00",
        })

    feats = shop.get("features", {})
    if feats.get("takeout"):
        node["hasOfferCatalog"] = {"@type": "OfferCatalog", "name": "お持ち帰り・お取り寄せ",
                                   "url": shop["keyPages"]["order"]}
    for label, key in (("テイクアウト", "takeout"), ("全国発送", "nationwideShipping"),
                       ("英語メニュー", "englishMenu"), ("お子様連れ歓迎", "kidsFriendly")):
        if feats.get(key):
            node["amenityFeature"].append(
                {"@type": "LocationFeatureSpecification", "name": label, "value": True})

    parking = shop.get("parking", {})
    if parking.get("available"):
        node["amenityFeature"].append({
            "@type": "LocationFeatureSpecification",
            "name": "駐車場（%d台）" % parking.get("spaces", 0),
            "value": True,
        })

    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": site + "/#website",
        "name": shop["name"],
        "url": shop["url"],
        "inLanguage": ["ja", "en"],
        "publisher": {"@id": site + "/#restaurant"},
    }
    return jsonld_block([node, website])


# --------------------------------------------------------------------- Menu


def build_menu(shop, menu):
    site = shop["url"].rstrip("/")
    sections = []
    for sec in menu["sections"]:
        items = []
        for it in sec["items"]:
            items.append({
                "@type": "MenuItem",
                "name": it["name"],
                "offers": {
                    "@type": "Offer",
                    "price": it["price"],
                    "priceCurrency": menu["currency"],
                },
            })
        sections.append({"@type": "MenuSection", "name": sec["section"], "hasMenuItem": items})

    node = {
        "@context": "https://schema.org",
        "@type": "Menu",
        "@id": site + "/menu.html#menu",
        "name": "%s お品書き" % shop["name"],
        "url": shop["keyPages"]["menu"],
        "inLanguage": "ja",
        "description": menu["note"],
        "hasMenuSection": sections,
        "provider": {"@id": site + "/#restaurant"},
    }
    return jsonld_block(node)


# ------------------------------------------------------------------ Products


def build_products(shop, products):
    site = shop["url"].rstrip("/")
    elements = []
    sellable = [x for x in products["items"] if x.get("price")]
    for i, p in enumerate(sellable, start=1):
        elements.append({
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "Product",
                "@id": "%s/order.html#%s" % (site, p["id"]),
                "name": p["name"],
                "description": p["description"],
                "brand": {"@type": "Brand", "name": shop["name"]},
                "offers": {
                    "@type": "Offer",
                    "price": p["price"],
                    "priceCurrency": products["currency"],
                    "availability": "https://schema.org/" + p.get("availability", "InStock"),
                    "url": products["shopUrl"],
                    "seller": {"@id": site + "/#restaurant"},
                },
            },
        })
    node = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "@id": site + "/order.html#products",
        "name": "%s お取り寄せ餃子" % shop["name"],
        "description": products["shippingNote"],
        "itemListElement": elements,
    }
    return jsonld_block(node)


# ----------------------------------------------------------------------- FAQ


def build_faq(shop, faq):
    site = shop["url"].rstrip("/")
    node = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "@id": site + "/#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": x["q"],
                "acceptedAnswer": {"@type": "Answer", "text": x["a"]},
            }
            for x in faq["items"]
        ],
    }
    return jsonld_block(node)


def build_faq_section(faq):
    """FAQPageは表示内容と一致していることが前提なので、表示用HTMLも生成する。"""
    rows = []
    for x in faq["items"]:
        rows.append(
            "    <details class=\"faq-item\">\n"
            "      <summary>%s</summary>\n"
            "      <p>%s</p>\n"
            "    </details>" % (x["q"], x["a"])
        )
    return (
        "<!-- よくあるご質問（FAQPage構造化データと文言を一致させること） -->\n"
        "<section class=\"section\" id=\"faq\">\n"
        "  <h2>よくあるご質問</h2>\n"
        "  <div class=\"faq-list\">\n"
        + "\n".join(rows) +
        "\n  </div>\n</section>\n"
    )


# --------------------------------------------------------------- Breadcrumbs


BREADCRUMBS = [
    ("menu", "メニュー"),
    ("order", "ネットショップ"),
    ("about", "店舗紹介"),
    ("howto", "餃子の焼き方"),
    ("contact", "お問合わせ"),
    ("news", "ブログ"),
    ("gallery", "ギャラリー"),
]


def build_breadcrumbs(shop):
    out = {}
    for key, label in BREADCRUMBS:
        url = shop["keyPages"].get(key)
        if not url:
            continue
        node = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "ホーム", "item": shop["url"]},
                {"@type": "ListItem", "position": 2, "name": label, "item": url},
            ],
        }
        out[key] = jsonld_block(node)
    return out


# ------------------------------------------------------------------- llms.txt


def build_llms(shop, menu, products, faq):
    h = shop["hours"]
    a = shop["address"]
    lines = []
    add = lines.append
    add("# %s" % shop["name"])
    add("")
    add("> %s" % shop["description"])
    add("")
    add("## 店舗の基本情報")
    add("- 店名: %s (%s)" % (shop["name"], shop["nameEn"]))
    add("- 住所: 〒%s %s%s%s" % (a["postalCode"], a["addressRegion"], a["addressLocality"], a["streetAddress"]))
    add("- 電話: %s" % shop["telephoneDisplay"])
    add("- 営業時間: %s〜%s (ラストオーダー %s)" % (h["open"], h["close"], h["lastOrder"]))
    add("- 定休日: %s" % h["closedLabel"])
    add("- お休みの詳細: 当月と翌月のお休みはトップページのカレンダーに掲載")
    add("- アクセス: %s" % " / ".join(shop["access"]))
    add("- 駐車場: %d台（満車の場合は隣のコインパーキング）" % shop["parking"]["spaces"])
    add("- 支払い: %s（店舗）" % "・".join(shop["paymentAccepted"]))
    add("- お持ち帰り: 可 / 全国発送: 可 / オンライン予約: 不可（電話でご相談）")
    add("")
    add("## 主なページ")
    labels = [
        ("home", "トップページ（今月と来月のお休みカレンダー、お知らせ）"),
        ("menu", "お品書き（全%d品・税込価格）" % sum(len(s["items"]) for s in menu["sections"])),
        ("menuEn", "英語メニュー"),
        ("order", "お取り寄せ餃子の注文案内"),
        ("shop", "ネットショップ（BASE）"),
        ("howto", "冷凍餃子のおいしい焼き方"),
        ("about", "店舗紹介"),
        ("news", "お知らせとメディア掲載"),
        ("gallery", "写真とショート動画"),
        ("contact", "お問い合わせ"),
        ("hirakata", "枚方に来られた方へのご案内"),
    ]
    for key, desc in labels:
        url = shop["keyPages"].get(key)
        if url:
            add("- [%s](%s)" % (desc, url))
    add("")
    add("## 餃子（看板商品・税込）")
    for it in menu["sections"][0]["items"]:
        add("- %s: %s円（税込）" % (it["name"], yen(it["price"])))
    add("")
    add("## お取り寄せ（全国発送）")
    add("%s" % products["shippingNote"])
    for p in products["items"]:
        if p.get("price"):
            add("- %s: %s円（箱代込み・税込・送料別）— %s" % (p["name"], yen(p["price"]), p["description"]))
        else:
            add("- %s: 近日発売予定 — %s" % (p["name"], p["description"]))
    add("")
    add("## メディア掲載")
    for m in shop["media"]:
        add("- %s %s%s" % (m["date"], m["outlet"], "（%s）" % m["note"] if m.get("note") else ""))
    add("")
    add("## よくあるご質問")
    for x in faq["items"][:6]:
        add("- Q. %s" % x["q"])
        add("  A. %s" % x["a"])
    add("")
    add("## 引用時のお願い")
    add("- 営業日・お休みは変動します。最新のお休みはトップページのカレンダーをご参照ください。")
    add("- 価格は税込で、仕入れ状況により変わる場合があります。")
    add("")
    short = "\n".join(lines) + "\n"

    # llms-full.txt はメニュー全文とFAQ全文を含む
    full = [short.rstrip("\n"), "", "## メニュー全文（税込）"]
    for sec in menu["sections"]:
        full.append("")
        full.append("### %s" % sec["section"])
        if sec["section"] == "定食":
            full.append(menu["setMealNote"])
        for it in sec["items"]:
            full.append("- %s: %s円" % (it["name"], yen(it["price"])))
    full.append("")
    full.append("## よくあるご質問（全文）")
    for x in faq["items"]:
        full.append("")
        full.append("### %s" % x["q"])
        full.append(x["a"])
    return short, "\n".join(full) + "\n"


# ------------------------------------------------------------ robots 追記分


ROBOTS_APPEND = """
# --- AIクローラの方針（2026-08-18 社長決定: 全許可） ---
# 生成AIの検索・要約に引用されることを目的として明示的に許可する。
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Bingbot
Allow: /

User-agent: CCBot
Allow: /
"""


# --------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    args = ap.parse_args()

    shop = strip_comments(load("shop.json"))
    menu = strip_comments(load("menu.json"))
    products = strip_comments(load("products.json"))
    faq = strip_comments(load("faq.json"))

    outdir = args.out
    jsonld_dir = os.path.join(outdir, "jsonld")
    os.makedirs(jsonld_dir, exist_ok=True)

    written = []

    def write(path, text):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        written.append(os.path.relpath(path, ROOT))

    write(os.path.join(jsonld_dir, "restaurant.html"), build_restaurant(shop))
    write(os.path.join(jsonld_dir, "menu.html"), build_menu(shop, menu))
    write(os.path.join(jsonld_dir, "products.html"), build_products(shop, products))
    write(os.path.join(jsonld_dir, "faq.html"), build_faq(shop, faq))
    for key, block in build_breadcrumbs(shop).items():
        write(os.path.join(jsonld_dir, "breadcrumb_%s.html" % key), block)

    write(os.path.join(outdir, "faq_section.html"), build_faq_section(faq))

    short, full = build_llms(shop, menu, products, faq)
    write(os.path.join(outdir, "llms.txt"), short)
    write(os.path.join(outdir, "llms-full.txt"), full)
    write(os.path.join(outdir, "robots_append.txt"), ROBOTS_APPEND.lstrip("\n"))

    print("生成しました:")
    for p in written:
        print("  " + p)


if __name__ == "__main__":
    main()
