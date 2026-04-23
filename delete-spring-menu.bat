@echo off
chcp 65001 >nul
REM ==============================================
REM Delete spring menu article and push
REM (run once, then you can delete this file)
REM ==============================================

cd /d "%~dp0"

echo.
echo =============================================
echo  Deleting spring menu article...
echo =============================================
echo.

REM Remove the post file from git
git rm "_posts/2026-04-20-spring-menu.md"

echo.
echo === Committing ===
git commit -m "Remove spring menu article (content not applicable)"

echo.
echo === Pushing to GitHub ===
git push origin main

echo.
echo =============================================
echo  Deletion complete!
echo  You can delete this .bat file after this.
echo =============================================
echo.
pause
