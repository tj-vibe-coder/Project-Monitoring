@echo off
echo === DS Monitoring App Installer ===
echo.

REM Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install/upgrade pip
python -m pip install --upgrade pip

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env file exists
if not exist ".env" (
    echo Creating .env file...
    echo DATABASE_URL=postgresql://postgres:wjchRTSfUzgSSpNXIeYrTVQayOnHqxNR@mainline.proxy.rlwy.net:59614/railway > .env
)

REM Create desktop shortcut
echo Creating desktop shortcut...
echo @echo off > "%USERPROFILE%\Desktop\DS Monitoring.bat"
echo cd /d "%~dp0" >> "%USERPROFILE%\Desktop\DS Monitoring.bat"
echo call venv\Scripts\activate >> "%USERPROFILE%\Desktop\DS Monitoring.bat"
echo python main.py >> "%USERPROFILE%\Desktop\DS Monitoring.bat"

REM Create start menu shortcut
echo Creating start menu shortcut...
if not exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\DS Monitoring" (
    mkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\DS Monitoring"
)
copy "%USERPROFILE%\Desktop\DS Monitoring.bat" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\DS Monitoring"

echo.
echo Installation complete!
echo.
echo You can now start the application using:
echo 1. The desktop shortcut
echo 2. The start menu shortcut
echo 3. Running this installer again
echo.

REM Ask if user wants to start the application now
set /p START_NOW="Would you like to start the application now? (Y/N) "
if /i "%START_NOW%"=="Y" (
    python main.py
)

pause 