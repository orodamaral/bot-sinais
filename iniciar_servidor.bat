@echo off
title Gold Macro Compass - Server
cd /d "%~dp0"
echo Iniciando Webhook Server...
start "Webhook Server" /min cmd /c "venv\Scripts\python.exe -m bot.webhook_server 5054"
timeout /t 3 >nul
echo Iniciando Ngrok Tunnel...
start "Ngrok Tunnel" /min cmd /c "ngrok http 5054 --log=stdout"
echo.
echo Aguarde 5 segundos e acesse: http://127.0.0.1:4040
echo Copie a URL https://xxxx.ngrok-free.app para o TradingView
echo.
pause
