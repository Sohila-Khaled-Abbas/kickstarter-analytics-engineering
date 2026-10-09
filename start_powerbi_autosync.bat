@echo off
TITLE Power BI Git Auto-Sync Daemon - Kickstarter Analytics Engineering
COLOR 0A

echo ===============================================================================
echo          KICKSTARTER POWER BI AUTOMATED GIT VERSION CONTROL DAEMON
echo ===============================================================================
echo.
echo This watcher automatically monitors your Power BI Desktop project (.pbip).
echo Every time you save your report or semantic model in Power BI Desktop:
echo    1. Automatically detects updated TMDL, expressions, and report JSON files.
echo    2. Debounces to ensure Power BI finishes writing.
echo    3. Stages and commits with timestamped message.
echo    4. Automatically pushes updates directly to GitHub!
echo.
echo Keep this window open minimized while working in Power BI Desktop.
echo Press Ctrl+C at any time to stop auto-sync.
echo ===============================================================================
echo.

cd /d "%~dp0"
python src\auto_sync_powerbi.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python auto-sync daemon exited with error code %ERRORLEVEL%.
    pause
)
