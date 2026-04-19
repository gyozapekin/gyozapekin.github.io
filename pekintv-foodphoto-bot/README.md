# pekintv-foodphoto-bot

大阪の餓子店「北京（ペキン）」の料理写真を **Box Sync フォルダで自動検知 → AI 加工 → SNS ドラフト化** するボット。
Windows 上で常駐し、新しい写真が `01_originals/` に入ると Gemini 2.5 Flash Image（Nano Banana）で 3 バリアントを生成、Vision で品質評価し、X / Instagram 用キャプションまで下書きして `03_drafts/` に出力する。**SNS 自動投稿はしない**（オーナーが Claude Code でレビュー → 承認 → 手動投稿）。

## セットアップ（Windows）

前提: Python 3.11+ が PATH に入っていること（`pythonw.exe` も使う）。Box Sync が動作しているユーザーセッションで運用する。

### 1. 依存インストール
```powershell
cd C:\pekintv-foodphoto-bot
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

### 2. `.env` 作成
`.env.example` を `.env` にコピーして埋める。

```
GEMINI_API_KEY=AIza...                                # https://aistudio.google.com/apikey で発行
GEMINI_BILLING_MODE=ai_studio                         # 通常これでOK。Proクレジット使うなら vertex
BOX_WATCH_DIR=D:\BOX_PekinTV\Box Sync\北京-写真DB\01_originals
DRAFT_OUTPUT_DIR=D:\BOX_PekinTV\Box Sync\北京-写真DB\03_drafts
APPROVED_DIR=D:\BOX_PekinTV\Box Sync\北京-写真DB\04_approved
REJECTED_DIR=D:\BOX_PekinTV\Box Sync\北京-写真DB\99_rejected
LOG_DIR=D:\BOX_PekinTV\Box Sync\北京-写真DB\_logs
```

### 3. 単発テスト（常駐させる前）
```powershell
python scripts\process_one.py "D:\BOX_PekinTV\Box Sync\北京-写真DB\01_originals\some_photo.jpg"
```
`03_drafts/` に新しいフォルダができ、バリアント 3 枚 + 2 キャプション + `critique.md` が入っていれば OK。

### 4. 常駐化（Task Scheduler）
```powershell
.\scripts\install_task.ps1
```
ログオフ → ログオン。以降、`01_originals/` に写真が入ると自動処理される。

### 5. Claude Code でレビュー
Claude Code を起動して `/pekintv-foodphoto` を呼ぶ。最新ドラフトの要約 → 承認 / 再生成 / キャプション編集 / 却下の対話フローに入る。

## Gemini 課金について

オーナーが加入している **Google AI Pro サブスクは Web アプリ向け**で、API の従量課金には含まれない。ただし:

- **AI Studio 無料枠**: Nano Banana（`gemini-2.5-flash-image`）は 1 日 500 枚まで無料。本ボットの想定利用（1 日 5 枚 × 3 バリアント = 15 枚）なら **実質 $0/月** で運用できる。
- **Pro 付帯の $10 GCP クレジット**: Google Developer Program 経由で毎月 $10 分の Google Cloud クレジットが発行される。`.env` の `GEMINI_BILLING_MODE=vertex` と `GCP_PROJECT_ID` を設定すると Vertex AI 経由に切り替わり、そのクレジットを消費できる。
- **月次利用量を確認**: `python scripts\usage_report.py` で今月の生成枚数・推定コスト・無料枠残りが出る。

## 開発（Linux/macOS でも可）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -v                  # 21 tests, モックのみで実 API コール無し
```

## ディレクトリ

| パス | 用途 |
|---|---|
| `src/pekintv_bot/` | ボット本体 |
| `scripts/process_one.py` | 単発処理（テスト・SKILL から呼ぶ） |
| `scripts/run_watcher.pyw` | Task Scheduler エントリ（コンソール非表示） |
| `scripts/install_task.ps1` | ONLOGON タスク登録 |
| `scripts/usage_report.py` | 月次コストサマリ |
| `.claude/skills/pekintv-foodphoto/` | Claude Code スキル定義 |
| `tests/` | pytest（モック） |
