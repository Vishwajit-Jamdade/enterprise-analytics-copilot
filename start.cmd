@echo off
setlocal
set ROOT_DIR=%~dp0

echo Starting backend on http://127.0.0.1:8001
start "Enterprise Assistant Backend" cmd /k cd /d "%ROOT_DIR%" ^&^& python -m uvicorn backend.app:app --reload --port 8001

echo Starting frontend on http://127.0.0.1:5173
start "Enterprise Assistant Frontend" cmd /k cd /d "%ROOT_DIR%frontend" ^&^& npm.cmd run dev

endlocal
