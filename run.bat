@echo off
echo Starting Qlib system...

REM Kill existing processes
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
timeout /t 1 /nobreak >nul

REM Create log directory
mkdir logs 2>nul

REM Start API server
echo Starting API server...
start "API Server" python api_server.py

REM Wait for API server to start
timeout /t 3 /nobreak >nul

REM Start WebSocket server
echo Starting WebSocket server...
start "WebSocket Server" node websocket_server.js

REM Wait for WebSocket server to start
timeout /t 2 /nobreak >nul

REM Start frontend
echo Starting frontend...
cd qlib-frontend
start "Frontend" npm start
cd ..

REM Wait for frontend to start
timeout /t 8 /nobreak >nul

REM Open browser
echo Opening browser...
start http://localhost:3009

echo.
echo All services started!
echo API server: http://localhost:8080
echo WebSocket server: ws://localhost:8080/ws
echo Frontend: http://localhost:3009
echo.
echo Press Ctrl+C to stop all services
pause
