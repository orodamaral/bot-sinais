$root = "C:\Users\Rod\Desktop\DEV\00_Trade\XauUSDTradingBot"
$venvPy = "$root\venv\Scripts\python.exe"
$port = 5054

Write-Host "[1/4] Iniciando Webhook Server..." -ForegroundColor Cyan
$ws = Start-Process -PassThru -WindowStyle Hidden $venvPy -ArgumentList "-m bot.webhook_server $port" -WorkingDirectory $root
Start-Sleep 3

if ((netstat -ano | findstr ":$port").Length -eq 0) {
    Write-Host "ERRO: Servidor nao iniciou" -ForegroundColor Red
    exit 1
}
Write-Host "      OK - porta $port" -ForegroundColor Green

Write-Host "[2/4] Iniciando Ngrok Tunnel..." -ForegroundColor Cyan
$ng = Start-Process -PassThru -WindowStyle Hidden ngrok -ArgumentList "http $port --log=stdout" -WorkingDirectory $root
Start-Sleep 4

Write-Host "[3/4] Obtendo URL publica..." -ForegroundColor Cyan
try {
    $api = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -ErrorAction Stop
    $url = $api.tunnels[0].public_url
    Write-Host "      URL: $url" -ForegroundColor Green
} catch {
    Write-Host "      AVISO: Nao foi possivel obter URL automaticamente" -ForegroundColor Yellow
    Write-Host "      Acesse http://127.0.0.1:4040 no navegador" -ForegroundColor Yellow
    $url = "?"
}

Write-Host "[4/4] Testando webhook..." -ForegroundColor Cyan
try {
    $resp = Invoke-RestMethod -Uri "$url/webhook" -Method POST -Body '{"signal":"BUY"}' -ContentType "application/json" -ErrorAction Stop
    Write-Host "      Resposta: $($resp | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "      Teste manual falhou: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  TUDO PRONTO!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "URL do Webhook (para o TradingView):" -ForegroundColor Cyan
Write-Host "$url/webhook" -ForegroundColor White
Write-Host ""
Write-Host "Exemplo de JSON para o alerta:" -ForegroundColor Cyan
Write-Host '{"signal":"STRONG BUY"}' -ForegroundColor White
Write-Host ""
Write-Host "Painel Ngrok: http://127.0.0.1:4040" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pressione qualquer tecla para parar tudo..."
pause

Stop-Process $ws -Force -ErrorAction SilentlyContinue
Stop-Process $ng -Force -ErrorAction SilentlyContinue
Write-Host "Servidores parados." -ForegroundColor Yellow
