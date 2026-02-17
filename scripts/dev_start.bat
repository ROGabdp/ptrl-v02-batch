@echo off
title PTRL Dev Launcher
echo Starting PTRL-v02 Dev Environment...

:: Change to repo root
cd /d %~dp0..

:: Check if .venv exists
if not exist .venv\Scripts\activate.bat (
    echo Error: .venv not found. Please run "python -m venv .venv" first.
    pause
    exit /b 1
)

:: Cleanup existing processes (optional, helps prevent duplicates)
echo Cleaning up previous instances (if any)...
taskkill /IM uvicorn.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
:: Note: We don't kill python.exe indiscriminately as it might kill other tools.

:: Activate venv
call .venv\Scripts\activate.bat

:: Start Backend
echo Starting Backend (Port 8000)...
start "PTRL Backend" cmd /k "python -m uvicorn api.app:app --reload --port 8000"

:: Start Frontend
echo Starting Frontend (Port 5173)...
cd ui
start "PTRL Frontend" cmd /k "npm run dev"

:: Open Browser
echo Waiting for services to initialize...
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo Development environment started!
echo - Backend: http://127.0.0.1:8000/docs
echo - Frontend: http://localhost:5173
echo.
echo Close the "PTRL Backend" and "PTRL Frontend" windows to stop servers.
pause
