@echo off
echo ===== 启动Qlib系统 =====

:: 杀死已存在的进程
echo 正在清理已有进程...
taskkill /F /IM node.exe /FI "WINDOWTITLE ne Administrator*" > nul 2>&1
taskkill /F /IM python.exe > nul 2>&1
timeout /t 1 /nobreak > nul

:: 创建日志目录
if not exist logs mkdir logs

:: 设置环境变量
set PORT=8080
set REACT_APP_API_URL=http://localhost:8080/api
set REACT_APP_WS_URL=ws://localhost:8080/ws

:: 修改API服务器CORS配置
echo 正在启动API服务器 (端口: 8080)...
start "Qlib API Server" cmd /c "python api_server.py > logs\api-server.log 2>&1"

:: 等待API服务器启动
timeout /t 3 /nobreak > nul

:: 启动WebSocket服务器
echo 正在启动WebSocket服务器 (端口: 8080)...
start "Qlib WebSocket Server" cmd /c "node websocket_server.js > logs\websocket-server.log 2>&1"

:: 等待WebSocket服务器启动
timeout /t 2 /nobreak > nul

:: 启动前端应用
echo 正在启动前端应用 (端口: 3009)...
cd qlib-frontend
start "Qlib Frontend" cmd /c "npm start > ..\logs\frontend.log 2>&1"
cd ..

:: 等待前端应用启动
timeout /t 8 /nobreak > nul

:: 打开浏览器
echo 正在打开浏览器...
start http://localhost:3009

echo.
echo ===== Qlib系统已启动! =====
echo API服务器: http://localhost:8080
echo WebSocket服务器: ws://localhost:8080/ws
echo 前端应用: http://localhost:3009
echo 日志文件: %cd%\logs
echo.
echo 提示: 如果页面显示错误，请等待10秒后刷新浏览器
echo.
echo 按任意键停止所有服务...
pause > nul

:: 停止所有服务
echo 正在停止所有服务...
taskkill /F /IM node.exe /FI "WINDOWTITLE ne Administrator*" > nul 2>&1
taskkill /F /IM python.exe > nul 2>&1

echo 所有服务已停止!
