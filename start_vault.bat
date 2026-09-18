@echo off
title Antra Security System
echo Starting Antra Security System...
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe run.py
) else (
    python run.py
)
pause
