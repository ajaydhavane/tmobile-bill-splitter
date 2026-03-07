@echo off
cd /d "%~dp0"

where uv >nul 2>&1
if %errorlevel% neq 0 (
	powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
)

echo Do not close this window until you are done using the app.
uv sync >nul 2>&1
uv run streamlit run main.py >nul
pause