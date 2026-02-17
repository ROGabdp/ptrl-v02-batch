@echo off
echo Stopping PTRL-v02 Dev Environment...

:: 1. Force Kill by Port (Most reliable for servers)
echo Killing Backend on Port 8000...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }" >nul 2>&1

echo Killing Frontend on Port 5173...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }" >nul 2>&1

:: 2. Close the Wrapper Windows (Cosmetic)
echo Closing CMD windows...
taskkill /FI "WINDOWTITLE eq PTRL Backend" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq PTRL Frontend" /T /F >nul 2>&1

:: 3. Cleanup Node (fallback)
taskkill /IM node.exe /F >nul 2>&1

echo.
echo Servers stopped.
pause
