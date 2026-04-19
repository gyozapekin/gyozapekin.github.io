---
name: pekintv-foodphoto
description: Review, regenerate, and approve PekinTV food photo drafts produced by the auto-enhancement pipeline.
---

# PekinTV 料理写真ドラフト レビュースキル

`scripts/run_watcher.pyw` が自動生成したドラフトをオーナーと一緒にレビューする。

## 前提
- `.env` の `DRAFT_OUTPUT_DIR` にドラフトフォルダが並んでいる
- 各フォルダには variants, captions, critique.json/md, metadata.json, original.jpg が入っている

## 実行時の手順
1. 最新 5 個のドラフトフォルダを mtime 順で表示（料理名・推奨バリアント・総評付）
2. 選ばれたドラフトの `critique.md` / キャプションを提示
3. アクション:
   - **承認**: `04_approved/` へ移動
   - **再生成**: `python scripts/process_one.py <original> --style <wood|overhead|backlight|custom "...">`
   - **キャプション編集**: `caption_x.txt` / `caption_instagram.txt` を Claude が直接修正
   - **却下**: `99_rejected/` へ移動
4. 文体は `references/style_guide_ja.md` に従う

## テストモード
画像パスを渡されたら `process_one.py <path>` を実行し、生成されたドラフトを提示しフィードバックを受け付ける。

## 禁止事項
- **SNS 自動投稿はしない**
- API キーを表示しない
- `04_approved` / `99_rejected` 以外のフォルダを書き換えない
