python .\merge_data.py

if %errorlevel% neq 0 (
    echo Error: merge data execution failed.
    pause
    exit /b 1
)

echo merge_data completed!
