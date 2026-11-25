@echo off
title DeepPrice-MM Dynamic Pricing Engine
cd /d "F:\multimodal_dynamic_pricing"
"F:\competitor_pricing_intel\.venv\Scripts\python.exe" "F:\multimodal_dynamic_pricing\launch_app.py"
if %errorlevel% neq 0 (
    echo.
    echo An error occurred while launching DeepPrice-MM.
    pause
)
