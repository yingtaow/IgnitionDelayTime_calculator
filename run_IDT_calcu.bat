REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please ensure Python is installed and added to system environment variables.
    pause
    exit /b 1
)

REM Set working directory to the script's directory
cd /d "%~dp0"

echo Current working directory: %cd%

REM Step 1: Run data generation script
echo. 
echo Starting data generation...
echo. 
python DataBuilder_paraV8.py

if %errorlevel% neq 0 (
    echo Error: Data generation script execution failed.
    pause
    exit /b 1
)

echo Data generation completed!

pause