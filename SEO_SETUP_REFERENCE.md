# 海鮮餃子 北京 - SEO/インフラ設定リファレンス

最終更新: 2026年6月2日
このファイルは gyozapekin.com のSEO設定・インフラ構成の完全リファレンスです。

---

## 1. プロジェクト基本情報

| 項目 | 値 |
|------|-----|
| 店舗名 | 海鮮餃子 北京（大阪府枚方市宮之阪） |
| 公式ドメイン | gyozapekin.com |
| 旧ドメイン | gyozapekin.github.io（リダイレクト元として残存） |
| GitHubリポジトリ | github.com/gyozapekin/gyozapekin.github.io |
| ローカル作業ディレクトリ | C:\Users\mydea\OneDrive\000_AI_Folder\Web_Pages\gyozapekin.github.io |
| メインGmail | kaisen.gyoza.pekin@gmail.com |

---

## 2. インフラ構成

```
[ユーザーのブラウザ]
        ↓
[gyozapekin.com 名前解決]
        ↓
[Cloudflare DNS]  ←── DNS管理はCloudflare（既に移行済み）
        ↓ Aレコード 185.199.108.153 / 185.199.109.153
        ↓
[GitHub Pages]  ←── ホスティング（main ブランチからビルド）
        ↓
[サイト表示]
```

### ドメインレジストラ
- **お名前.com**（ドメイン契約・更新請求はここ）

### DNS管理
- **Cloudflare** （アカウント: Kaisen.gyoza.pekin@gmail.com）
- ネームサーバーがCloudflareに移管済み
- ダッシュボード: https://dash.cloudflare.com/

### ホスティング
- **GitHub Pages**
- Settings → Pages: Custom domain = gyozapekin.com、Enforce HTTPS = ON
- ソース: main ブランチ / (root)
- リポジトリ: https://github.com/gyozapekin/gyozapekin.github.io

---

## 3. Google Search Console 登録状態

| プロパティ種別 | 値 | 所有権確認方法 |
|------|-----|--------------|
| URLプレフィックス | https://gyozapekin.com | HTMLファイル (google7882b477a4884e43.html) |
| ドメイン | gyozapekin.com | DNS TXT (Cloudflare経由で自動追加) |

### 所有権確認ファイル
- ファイル名: `google7882b477a4884e43.html`
- 場所: リポジトリのルート
- 中身: `google-site-verification: google7882b477a4884e43.html`
- 削除厳禁（削除すると所有権確認が外れる）

### TXTレコード（Cloudflare に登録済み）
- Name: `gyozapekin.com`
- Type: TXT
- Content: `"google-site-verification=Hy0KGW_-3_KX-wQ1NMd2ikrrj5qD79cGvux3P5FrE6U"`
- 削除厳禁

### sitemap.xml
- 場所: https://gyozapekin.com/sitemap.xml
- 登録URL数: 15ページ（日本語版 + 英語版）
- Search Consoleで「成功しました」ステータス

---

## 4. SEO 設計ルール（重要）

すべて gyozapekin.com に統一すること。github.io は使わない。

### canonical 設定（全HTMLページ）
```html
<link rel="canonical" href="https://gyozapekin.com/{ページパス}">
```

### OGP / Twitter Card
```html
<meta property="og:url" content="https://gyozapekin.com/{ページパス}">
<meta property="og:image" content="https://gyozapekin.com/images/{画像}">
<meta name="twitter:image" content="https://gyozapekin.com/images/{画像}">
```

### hreflang（日本語/英語切替）
```html
<link rel="alternate" hreflang="ja" href="https://gyozapekin.com/{パス}">
<link rel="alternate" hreflang="en" href="https://gyozapekin.com/en/{パス}">
<link rel="alternate" hreflang="x-default" href="https://gyozapekin.com/{パス}">
```

### sitemap.xml と robots.txt
- sitemap.xml の全 `<loc>` は gyozapekin.com で始まる
- robots.txt の Sitemap 行も gyozapekin.com

### canonical が必要なページ一覧（合計12ページ）
| ファイル | canonical URL |
|------|-----|
| index.html | https://gyozapekin.com/ |
| menu.html | https://gyozapekin.com/menu.html |
| about.html | https://gyozapekin.com/about.html |
| contact.html | https://gyozapekin.com/contact.html |
| howto.html | https://gyozapekin.com/howto.html |
| privacy.html | https://gyozapekin.com/privacy.html |
| en/index.html | https://gyozapekin.com/en/index.html |
| en/menu.html | https://gyozapekin.com/en/menu.html |
| en/about.html | https://gyozapekin.com/en/about.html |
| en/contact.html | https://gyozapekin.com/en/contact.html |
| en/howto.html | https://gyozapekin.com/en/howto.html |
| en/privacy.html | https://gyozapekin.com/en/privacy.html |

---

## 5. 重要な作業ファイル（リポジトリルート）

### 削除厳禁
- `google7882b477a4884e43.html` - Search Console所有権確認ファイル
- `.nojekyll` - GitHub PagesでJekyll処理を無効化
- `sitemap.xml` - 検索エンジン向けサイトマップ
- `robots.txt` - クローラー制御

### バッチファイル（push用）
- `push_homepage.bat` - 通常の index.html push 用
- `push_seo_fix.bat` - SEO修正の push 用テンプレート
- `push_google_verify.bat` - Search Console確認ファイル push 用

### ログ（削除可）
- `push_homepage_result.log`
- `push_seo_fix_result.log`
- `push_google_verify_result.log`

---

## 6. 既知の問題と対処法

### 問題A: OneDrive が .git フォルダを同期 → git index.lock が頻発
**症状**: `fatal: Unable to create '.git/index.lock': File exists`

**原因**: OneDrive が `.git/` ディレクトリ内のファイルをロックする

**対処法**:
1. bat ファイルの先頭で `del /F /Q .git\index.lock` を実行
2. サンドボックスからは `mv .git/index.lock .git/index.lock.old` で回避可能
3. 根本対策: OneDrive の除外設定で `.git` フォルダを除外する（未実施）

### 問題B: サンドボックスから git push できない
**症状**: `fatal: could not read Username for 'https://github.com'`

**原因**: PAT (Personal Access Token) は Windows Credential Manager に格納されており、Linuxサンドボックスからアクセス不可

**対処法**: Windows側のbatファイルから push する（Credential Manager 経由でPAT自動取得）

### 問題C: gyozapekin.com にアクセスできない（DNS_PROBE_FINISHED_NXDOMAIN）
**症状**: 最初の確認時に発生

**原因**: ローカルDNSキャッシュの問題

**対処法**: 
1. `ipconfig /flushdns` でDNSキャッシュをクリア
2. ブラウザ再起動
3. 別のDNSサーバー（8.8.8.8 等）で確認

実際のDNSは正常に解決されている（world-wide で 185.199.108.153 を返す）

### 問題D: GitHub Pages デプロイ後、ファイルが404
**症状**: push 直後にURLにアクセスすると404が出る

**原因**: GitHub Pages のビルドが完了していない

**対処法**: 1〜2分待つ（github.com/{user}/{repo}/actions でビルド進捗確認可）

---

## 7. 標準作業フロー

### コード変更を push する手順
1. ローカル（OneDrive）で編集
2. `push_homepage.bat` 等のバッチファイルを実行
   - ファイル名を指定して実行（Win+R）→ `cmd /c "C:\Users\mydea\OneDrive\000_AI_Folder\Web_Pages\gyozapekin.github.io\push_xxx.bat"`
   - または Explorer から直接ダブルクリック
3. `push_xxx_result.log` で結果確認

### バッチファイルの基本テンプレート
```bat
@echo off
cd /d "%~dp0"
set LOGFILE=%~dp0push_result.log
echo === START %DATE% %TIME% === > "%LOGFILE%"

REM ステップ1: 古いロック削除（OneDrive対策）
if exist ".git\index.lock" del /F /Q ".git\index.lock" >> "%LOGFILE%" 2>&1

REM ステップ2: 必要に応じて origin と同期
git fetch origin >> "%LOGFILE%" 2>&1

REM ステップ3: ファイルをadd
git add {対象ファイル} >> "%LOGFILE%" 2>&1

REM ステップ4: commit
git commit -m "{コミットメッセージ}" >> "%LOGFILE%" 2>&1

REM ステップ5: push
git push origin main >> "%LOGFILE%" 2>&1

echo === END %DATE% %TIME% === >> "%LOGFILE%"
exit
```

---

## 8. 本日（2026/06/02）行った作業の履歴

### コミット履歴（時系列）
1. `2e90d64` - Fix SEO: canonical/OGP/sitemap を gyozapekin.com に統一
2. `7d61c8b` - Merge branch 'main' into seo-fix-canonical-com-v2
3. `a6c5464` - PR #2 を main にマージ
4. `c032747` - Add Google Search Console verification file

### Pull Request
- PR #2: https://github.com/gyozapekin/gyozapekin.github.io/pull/2
- タイトル: Fix SEO: canonical/OGP/sitemap を gyozapekin.com に統一
- マージ済み

### 修正したファイル（14ファイル）
- HTML: about, contact, howto, index, menu, privacy（日本語版+英語版で12ファイル）
- robots.txt
- sitemap.xml

### 追加したファイル
- google7882b477a4884e43.html

---

## 9. SEO効果の確認方法

### 日々の確認
- Google検索で `site:gyozapekin.com` を実行 → インデックスされているページ数を確認
- Google検索で `site:gyozapekin.github.io` を実行 → 徐々にゼロに近づくはず

### Search Consoleでの確認
- 「URL検査」: 個別ページのインデックス状態とクロール日時
- 「ページ」: 全ページの登録状況
- 「検索パフォーマンス」: 実際の検索クエリと表示・クリック数

### 検索順位の目安
- 1週間: クロール反映開始
- 2週間: canonical の切り替えが反映
- 1〜2ヶ月: 検索順位が安定

---

## 10. 今後の TODO（順位）

### 短期（1〜2週間）
- [ ] SNS（X、Instagram）のプロフィールURL欄を gyozapekin.com に統一
- [ ] 食べログ・ホットペッパーグルメの店舗ページのURLを gyozapekin.com に変更
- [ ] Googleマップの店舗情報のWEBサイト欄を gyozapekin.com に確認

### 中期（1〜2ヶ月）
- [ ] SEO効果の確認（site: 検索、検索順位）
- [ ] gyozapekin.github.io 経由のトラフィックが減ったか確認
- [ ] インデックスエラーの月次チェック

### 長期（時期未定）
- [ ] Cloudflare Registrar へのドメイン移管検討
  - 前提: お名前.com で AuthCode 取得＋ Transfer Lock 解除
  - SEO的にはやり直しにならない（URLもDNSも変わらない）
  - 移管中の短時間ダウン注意

---

## 11. アクセス情報まとめ

| サービス | URL | アカウント |
|------|-----|--------|
| GitHubリポジトリ | https://github.com/gyozapekin/gyozapekin.github.io | gyozapekin |
| GitHub Pages設定 | https://github.com/gyozapekin/gyozapekin.github.io/settings/pages | - |
| Search Console | https://search.google.com/search-console | kaisen.gyoza.pekin@gmail.com |
| Cloudflare | https://dash.cloudflare.com/ | Kaisen.gyoza.pekin@gmail.com |
| お名前.com | https://www.onamae.com/ | 確認要 |
| 公開サイト | https://gyozapekin.com/ | - |
| BASEショップ | https://gyozapekin.official.ec/ | - |

---

このリファレンスは今後のSEO関連作業の起点として使用してください。
内容に変更があれば随時更新すること。
