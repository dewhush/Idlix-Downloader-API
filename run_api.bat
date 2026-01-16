@echo off
chcp 65001 >nul
cls

echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║                                                                   ║
echo ║     ██╗██████╗ ██╗     ██╗██╗  ██╗     █████╗ ██████╗ ██╗        ║
echo ║     ██║██╔══██╗██║     ██║╚██╗██╔╝    ██╔══██╗██╔══██╗██║        ║
echo ║     ██║██║  ██║██║     ██║ ╚███╔╝     ███████║██████╔╝██║        ║
echo ║     ██║██║  ██║██║     ██║ ██╔██╗     ██╔══██║██╔═══╝ ██║        ║
echo ║     ██║██████╔╝███████╗██║██╔╝ ██╗    ██║  ██║██║     ██║        ║
echo ║     ╚═╝╚═════╝ ╚══════╝╚═╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝     ╚═╝        ║
echo ║                                                                   ║
echo ║                   Created by: dewhush                             ║
echo ║        Original: sandrocods/IdlixDownloader                       ║
echo ║                                                                   ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.
echo Starting Idlix Downloader API...
echo.

:: Check if .env exists
if not exist ".env" (
    echo [WARNING] .env file not found! Copying from .env.example...
    copy .env.example .env >nul
    echo [INFO] Please edit .env file to set your API_KEY
    echo.
)

:: Run the API server
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

pause
