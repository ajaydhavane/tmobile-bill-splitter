@echo off
cd /d "%~dp0"

where uv >nul 2>&1
if %errorlevel% neq 0 (
	powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
)

echo Do not close this window until you are done using the app.

uv run streamlit run src/main.py >nul

echo.
echo Process finished. You can close this window.
pause
