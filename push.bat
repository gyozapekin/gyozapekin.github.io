@echo off
REM ==============================================
REM 自動コミット&プッシュスクリプト
REM 使い方: このファイルをダブルクリック
REM ==============================================

cd /d "%~dp0"

echo.
echo =============================================
echo  海鮮餃子 北京 - 自動コミット&プッシュ
echo =============================================
echo.

REM 変更されたファイルを確認
git status --short

echo.
set /p commitmsg="コミットメッセージを入力 (Enterでスキップ): "

if "%commitmsg%"=="" (
  set commitmsg=Update site content
)

echo.
echo === 変更をステージング ===
git add -A

echo.
echo === コミット ===
git commit -m "%commitmsg%"

echo.
echo === GitHub へプッシュ ===
git push origin main

echo.
echo =============================================
echo  完了！
echo  https://gyozapekin.github.io/news/
echo  で確認してください（1-2分後に反映）
echo =============================================
echo.
pause
