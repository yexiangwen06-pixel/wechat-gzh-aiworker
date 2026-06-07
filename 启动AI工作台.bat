@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ========================================
echo   微信公众号内容 AI 工作台
echo ========================================
echo.
echo 正在启动服务器...
echo 浏览器会自动打开：http://localhost:8765
echo.
echo 按 Ctrl+C 可以停止服务器
echo ========================================
echo.
python -m wechat_ai serve --port 8765
pause