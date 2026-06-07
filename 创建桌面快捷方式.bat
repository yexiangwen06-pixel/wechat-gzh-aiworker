@echo off
set "SCRIPT_PATH=%~dp0启动AI工作台.bat"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\启动AI工作台.bat.lnk"

echo 正在创建桌面快捷方式...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%SCRIPT_PATH%'; $s.Save()"

echo.
echo 桌面快捷方式已创建！
echo 双击桌面上的 "启动AI工作台.bat" 即可启动 AI 工作台
echo 浏览器会自动打开：http://localhost:8765
echo.
pause