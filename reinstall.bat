@echo off
echo Changing to knowledge engine directory...
cd /d "C:\Users\mddee\knowledge_engine"
echo.
echo Killing any running ke-server.exe processes...
taskkill /F /IM ke-server.exe 2>nul
timeout /t 2 /nobreak >nul
echo.
echo Building knowledge engine package...
uv build
echo.
echo Installing knowledge engine package...
uv pip install --system --force-reinstall .
echo.
echo Done!
pause 