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
