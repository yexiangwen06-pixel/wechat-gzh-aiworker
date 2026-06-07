@echo off
chcp 65001 >nul
title 公众号内容 AI 工作台
cd /d "%~dp0"

echo 正在清理旧的本地服务...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$lines = netstat -ano | Select-String ':8765' | Select-String 'LISTENING'; foreach ($line in $lines) { $parts = ($line.ToString() -split '\s+') | Where-Object { $_ }; $pid = [int]$parts[-1]; Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }"

echo 正在启动公众号内容 AI 工作台...
start "" cmd /c "timeout /t 2 >nul & start "" http://localhost:8765/"
"C:\Users\20103\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m wechat_ai --db .tmp\demo.db serve --port 8765
pause
