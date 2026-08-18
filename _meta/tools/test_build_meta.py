#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_meta.py の生成物を検証するテスト。

実行: python3 tools/test_build_meta.py
コード変更後は必ずこれを流す。
"""

import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FAILS = []
CHECKS = [0]


def check(cond, label):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(label)
        print("  NG  " + label)
    else:
        print("  ok  " + label)


def extract(path):
    """<script type=application/ld+json> の中身をJSONとして取り出す。"""
    text = open(path, encoding="utf-8").read()
    m = re.search(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', text, re.S)
    assert m, "script タグが見つからない: " + path
    return json.loads(m.group(1))


def main():
    out = tempfile.mkdtemp(prefix="pekin_meta_")
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_meta.py"), "--out", out],
                       capture_output=True, text=True)
    print("build_meta.py 終了コード:", r.returncode)
    check(r.returncode == 0, "build_meta.py が正常終了する")
    if r.returncode != 0:
        print(r.stderr)
        return 1

    j = os.path.join(out, "jsonld")

    # --- Restaurant ---
    nodes = extract(os.path.join(j, "restaurant.html"))
    check(isinstance(nodes, list) and len(nodes) == 2, "restaurant: RestaurantとWebSiteの2ノード")
    rest = nodes[0]
    for key in ("name", "address", "telephone", "url", "priceRange", "openingHoursSpecification",
                "hasMenu", "sameAs", "servesCuisine"):
        check(key in rest and rest[key], "restaurant: %s がある" % key)
    check(rest["@type"] == "Restaurant", "restaurant: @typeがRestaurant")
    check(rest["telephone"].startswith("+81"), "restaurant: 電話が国際表記")
    check(rest["address"]["postalCode"] == "573-0022", "restaurant: 郵便番号が正しい")
    check(rest["geo"]["latitude"] == 34.8137 and rest["geo"]["longitude"] == 135.6553, "restaurant: 緯度経度が入っている")

    specs = rest["openingHoursSpecification"]
    openspec = specs[0]
    check(openspec["opens"] == "11:30" and openspec["closes"] == "22:00", "restaurant: 営業時間 11:30-22:00")
    days = openspec["dayOfWeek"]
    check(not any("Tuesday" in d for d in days), "restaurant: 火曜が営業曜日に入っていない")
    check(not any("Wednesday" in d for d in days), "restaurant: 水曜が営業曜日に入っていない")
    check(len(days) == 5, "restaurant: 営業曜日が5日")
    closed = [s for s in specs[1:]]
    closed_days = " ".join(json.dumps(s, ensure_ascii=False) for s in closed)
    check("Tuesday" in closed_days and "Wednesday" in closed_days, "restaurant: 火水が休業として明示されている")
    props = {p["name"]: p["value"] for p in rest["additionalProperty"]}
    check(props.get("定休日") == "火曜日（水曜日は不定休）", "restaurant: 定休日表記が社長方針どおり")

    # --- Menu ---
    menu = extract(os.path.join(j, "menu.html"))
    src = json.load(open(os.path.join(ROOT, "data", "menu.json"), encoding="utf-8"))
    n_src = sum(len(s["items"]) for s in src["sections"])
    n_out = sum(len(s["hasMenuItem"]) for s in menu["hasMenuSection"])
    check(n_src == n_out, "menu: 品数が正本と一致 (%d)" % n_src)
    check(len(menu["hasMenuSection"]) == len(src["sections"]), "menu: セクション数が一致")
    prices = [i["offers"]["price"] for s in menu["hasMenuSection"] for i in s["hasMenuItem"]]
    check(all(isinstance(p, int) and p > 0 for p in prices), "menu: 価格が全て正の整数")
    names = [i["name"] for s in menu["hasMenuSection"] for i in s["hasMenuItem"]]
    check("海王餃子（2匹）" in names, "menu: 看板の海王餃子が入っている")

    # --- Products ---
    prod = extract(os.path.join(j, "products.html"))
    psrc = json.load(open(os.path.join(ROOT, "data", "products.json"), encoding="utf-8"))
    sellable = [x for x in psrc["items"] if x.get("price")]
    check(len(prod["itemListElement"]) == len(sellable), "products: 販売中の商品数が一致(価格未定は除外)")
    kaiou = [e["item"] for e in prod["itemListElement"] if e["item"]["name"] == "海王餃子セット"]
    check(kaiou and kaiou[0]["offers"]["price"] == 7760, "products: 海王餃子セットが7760円(本番order.html実測)")

    # --- FAQ ---
    faq = extract(os.path.join(j, "faq.html"))
    fsrc = json.load(open(os.path.join(ROOT, "data", "faq.json"), encoding="utf-8"))
    check(len(faq["mainEntity"]) == len(fsrc["items"]), "faq: 件数が一致")
    section = open(os.path.join(out, "faq_section.html"), encoding="utf-8").read()
    missing = [x["q"] for x in fsrc["items"] if x["q"] not in section]
    check(not missing, "faq: 表示用HTMLに全質問が載っている（構造化データと一致）")
    answers_missing = [x["q"] for x in fsrc["items"] if x["a"] not in section]
    check(not answers_missing, "faq: 表示用HTMLに全回答が載っている")

    # --- Breadcrumb ---
    bc = extract(os.path.join(j, "breadcrumb_menu.html"))
    check(bc["itemListElement"][1]["item"].endswith("menu.html"), "breadcrumb: menuのURLが正しい")

    # --- llms.txt ---
    llms = open(os.path.join(out, "llms.txt"), encoding="utf-8").read()
    for needle in ("海鮮餃子 北京", "072-849-0433", "11:30", "火曜日（水曜日は不定休）",
                   "宮之阪1-19-2", "https://gyozapekin.com/menu.html", "海王餃子セット"):
        check(needle in llms, "llms.txt: %s が載っている" % needle)
    full = open(os.path.join(out, "llms-full.txt"), encoding="utf-8").read()
    check(all(n in full for n in names), "llms-full.txt: メニュー全品が載っている")
    check(len(full) > len(llms), "llms-full.txt が llms.txt より詳しい")

    # --- 内部コメントの漏れがないこと ---
    for root, _dirs, files in os.walk(out):
        for fn in files:
            body = open(os.path.join(root, fn), encoding="utf-8").read()
            check("_comment" not in body and "_todo" not in body,
                  "%s に内部コメントが漏れていない" % fn)

    # --- robots 追記分 ---
    rob = open(os.path.join(out, "robots_append.txt"), encoding="utf-8").read()
    for bot in ("GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"):
        check("User-agent: %s" % bot in rob, "robots: %s の許可がある" % bot)
    check("Disallow" not in rob, "robots: 追記分に誤ってDisallowが入っていない")

    print("")
    print("チェック %d件 / 失敗 %d件" % (CHECKS[0], len(FAILS)))
    if FAILS:
        print("失敗した項目:")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("すべて合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
