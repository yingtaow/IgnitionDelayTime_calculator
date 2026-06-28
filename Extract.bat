python .\extract.py

if %errorlevel% neq 0 (
    echo Error: extract data execution failed.
    pause
    exit /b 1
)

echo extract data completed!
