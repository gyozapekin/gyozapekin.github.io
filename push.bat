@echo off
chcp 65001 >nul
REM Auto commit and push (fully automatic, no input required)
cd /d "%~dp0"

git add -A

REM Use timestamp as commit message for tracking
for /f "tokens=1-4 delims=/-: " %%a in ("%date% %time%") do set ts=%%a%%b%%c-%%d
git commit -m "Update site content (%ts%)"

git push origin main

REM Keep window open for 3 seconds to show result, then close
timeout /t 3 /nobreak >nul
exit
