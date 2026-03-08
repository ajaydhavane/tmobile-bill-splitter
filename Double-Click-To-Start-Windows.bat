@echo off
cd /d "%~dp0"

where uv >nul 2>&1
if %errorlevel% neq 0 (
	echo Installing dependencies...
	powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1
)

echo.
powershell -Command "Write-Host 'Do not close this window until you are done using the app!!!' -ForegroundColor Red"
echo.

uv run streamlit run src/main.py >nul
pause
