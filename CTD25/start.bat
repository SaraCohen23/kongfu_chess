@echo off
REM Windows batch script to run the chess game from the correct directory

echo Chess Game - Client/Server
echo ===========================

REM Change to the project root directory
cd /d %~dp0

REM Check if we're in the right directory
if not exist "pieces\board.csv" (
    echo Error: Cannot find pieces\board.csv
    echo Make sure you're running this from the CTD25_Solutions directory
    pause
    exit /b 1
)

REM Check if KFC_Py directory exists
if not exist "KFC_Py\run.py" (
    echo Error: Cannot find KFC_Py\run.py
    echo Make sure the KFC_Py directory exists
    pause
    exit /b 1
)

echo Project directory: %CD%
echo.

if "%1"=="server" (
    echo Starting Chess Game Server...
    python KFC_Py\run.py server
) else if "%1"=="client" (
    echo Starting Chess Game Client...
    python KFC_Py\run.py client
) else if "%1"=="console" (
    echo Starting Console Chess Game Client...
    python KFC_Py\run.py console
) else if "%1"=="install" (
    echo Installing requirements...
    python KFC_Py\run.py install
) else (
    echo Usage:
    echo   start.bat server    - Start the server
    echo   start.bat client    - Start a client with graphics
    echo   start.bat console   - Start a console-only client
    echo   start.bat install   - Install requirements
    echo.
    echo Example:
    echo   start.bat server
    echo   start.bat client
)

pause
