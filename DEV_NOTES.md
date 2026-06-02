# 開発メモ

このファイルは Git で管理する開発上の注意事項。

## Windows .bat ファイルの文字化け対策

**問題**: 日本語Windows環境でコマンドプロンプトはShift-JIS（CP932）で動作するため、
UTF-8で保存された .bat ファイルの日本語コメントが文字化けし、コマンド実行エラーになる。

**症状例**:
```
'ャ繧ｯ' は、内部コマンドまたは外部コマンド、操作可能なプログラムまたは
バッチ ファイルとして認識されていません。
```

**対策**:
1. .bat ファイルは **ASCII英語のみ** で記述する
2. どうしても日本語を使う場合は先頭に `chcp 65001 >nul` を入れる

**OK例**:
```bat
@echo off
chcp 65001 >nul
REM English comments
echo Done!
```

**NG例**:
```bat
@echo off
REM 日本語コメント  <- 文字化けする
echo 日本語メッセージ  <- 文字化けする
```

## Cowork mode 環境の制約

- 画面中央にClaudeのUIが常に表示されるため、GitHub Desktop等のクリック操作困難
- → バッチファイル運用（push.bat 等）を主軸にする

## Computer Use 自動化の検討事項（重要・継続検討）

**2026-04-24 判明事項**: Cowork mode でも Computer Use 経由で「File Explorerから .bat ファイルをダブルクリック」は成功する。
→ 非対話式バッチ化 + Computer Useトリガーで、コミット&プッシュを完全自動化できた。

### 今後継続検討すべきこと

1. **Chrome Browser の間接操作**
   - Chrome はtier "read" でクリック不可 → Chrome MCP（拡張機能）を使えば操作可能
   - OAuth認証、Gmail操作、カレンダー連携等は Chrome MCP 経由で実施可能か？
   - リダイレクト待ちなどでChromeの自動操作が止まる問題の回避策検討

2. **CMD/PowerShell への入力**
   - CMD/PowerShell はtier "click" で typing 不可
   - 対策: バッチ/PSスクリプトを事前に書いて、ダブルクリック実行
   - 対話式処理が必要な場合: 非対話式に書き換える（timeout、既定値設定等）

3. **GitHub Desktop のクリック操作**
   - tier "full" だが Cowork の黒マスクで隠れがち
   - → 必要なら押し出し（最小化/最大化/Alt+Tab）を試す
   - → そもそもバッチ運用に置き換え可能なら置き換える

4. **新規アプリインストール時のUAC/管理者権限ダイアログ**
   - Windows UIPI で操作不可 → ユーザー手動対応必須
   - 対策: インストーラーは事前にサイレントインストール版を使う等

5. **ファイル削除の権限**
   - mcp__cowork__allow_cowork_file_delete はユーザー対話必須
   - 代替: Jekyll の `published: false` 等でファイル残したまま非公開化
   - git rm + バッチ化 も選択肢

6. **セキュリティ検証（Cloudflare等）**
   - 5秒待ち画面やCAPTCHAは自動突破しない
   - 待ち時間を十分に取る。CAPTCHAが出たらユーザー介入

7. **マルチモニター対応**
   - switch_display で各モニターを確認できる
   - Cowork のマスクは主モニターに出ることが多い → 別モニターに移す案も検討

### 実証済み自動化パターン

| 作業 | 手段 | 状態 |
|---|---|---|
| ファイル作成・編集 | Write/Edit ツール | ✓ 実証済み |
| git commit & push | 非対話 push.bat + Computer Use double-click | ✓ 実証済み |
| リポジトリ状態確認 | Chrome MCP で github.com 閲覧 | ✓ 実証済み |
| サイト動作確認 | Chrome MCP で live site 閲覧 | ✓ 実証済み |
| ドメイン管理画面操作 | Chrome MCP (Jimdo, お名前.com, Cloudflare) | ✓ 実証済み |

### 未実証・要検討

- Windows File Explorer からの右クリックメニュー操作
- ドラッグ＆ドロップによるファイル移動
- パスワード認証が必要なアプリの操作（NordPass、1Passwordなど）
- メール本文の自動読み取り（Gmail MCP の活用）
- 動画録画・スクリーンキャプチャの自動化

## Jekyll の予約変数

以下の変数名は Jekyll 内部で自動生成されるため、カスタム値で上書き不可:
- `site.categories` → `site.news_categories` を使用
- `site.tags` → `site.news_tags` 等を使用
- 記事の `category:` フィールドも同様 → `news_category:` を使用

## 記事投稿の手順

1. `_posts/` に `YYYY-MM-DD-title.md` を作成
2. 先頭のFront Matterを記述（下記テンプレ参照）
3. `push.bat` をダブルクリックしてコミット＆プッシュ

### Front Matterテンプレ

```markdown
---
layout: post
title: "記事タイトル"
date: 2026-05-01 12:00:00 +0900
news_category: oshirase
description: "検索結果やSNSシェアに表示される説明文（120字以内推奨）"
---
```

### カテゴリID一覧

| ID | 表示名 |
|---|---|
| `media` | メディア情報 |
| `oshirase` | お知らせ |
| `oyasumi` | お休みのお知らせ |
| `oryori` | つぶやき・お料理 |

### 記事を非公開にする

Front Matter に `published: false` を追加するとJekyllビルド時に除外される。
```markdown
---
layout: post
title: "..."
published: false
---
```
