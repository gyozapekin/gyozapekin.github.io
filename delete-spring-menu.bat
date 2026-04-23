@echo off
REM ==============================================
REM 春の新メニュー記事を削除してプッシュ
REM （一度実行したら削除してOK）
REM ==============================================

cd /d "%~dp0"

echo.
echo =============================================
echo  春の新メニュー記事を削除します
echo =============================================
echo.

REM 記事ファイルを削除
git rm "_posts/2026-04-20-spring-menu.md"

echo.
echo === コミット ===
git commit -m "Remove spring menu article (content not applicable)"

echo.
echo === GitHub へプッシュ ===
git push origin main

echo.
echo =============================================
echo  削除完了！
echo  このbatファイル自体もこの後削除して大丈夫です
echo =============================================
echo.
pause
