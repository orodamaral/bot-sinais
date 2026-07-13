import threading, time, json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from bot.webhook_server import app
from bot.mt4_executor import MT4Executor

port = 5055
executor = MT4Executor()
executor.initialize()

def run_server():
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(2)

import requests

print(f"Servidor rodando em http://localhost:{port}")
print()

# test health
r = requests.get(f"http://localhost:{port}/health")
print(f"GET /health -> {r.status_code} {r.json()}")

# test webhook
for sig in ["BUY", "SELL", "STRONG BUY", "NEUTRAL"]:
    r = requests.post(f"http://localhost:{port}/webhook", json={"signal": sig})
    print(f"POST /webhook (signal={sig}) -> {r.status_code} {r.json()}")

print()
print("Testes concluidos. Servidor vai parar automaticamente.")
