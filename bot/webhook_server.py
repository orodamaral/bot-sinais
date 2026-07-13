import json
import logging
import sys
from pathlib import Path

from flask import Flask, request, jsonify

from .config import load_config
from .mt4_executor import MT4Executor
from .actions import run_actions

logger = logging.getLogger("webhook_server")
app = Flask(__name__)
executor = MT4Executor()
executor.initialize()


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    logger.info("Webhook recebido: %s", json.dumps(data, indent=2))

    action = (data.get("action") or "").strip().upper()
    ticker = data.get("ticker", "XAUUSD")
    price = data.get("price", 0)
    time_ms = data.get("time", 0)

    extra = {
        "ticker": ticker,
        "price": price,
        "time": time_ms,
        "action": action,
    }

    MT4_MAP = {
        "COMPRA": 2,
        "VENDA": -2,
        "TAKE": 0,
        "STOP LOSS": 0,
        "VIRADA DE MÃO": 0,
    }

    signal = MT4_MAP.get(action)
    if signal is None:
        return jsonify({"status": "ignored", "signal": action})

    if signal != 0:
        cfg = load_config()
        trade_cfg = cfg.get("trade", {})
        executor.send_signal(
            signal,
            trade_cfg.get("sl_points", 500),
            trade_cfg.get("tp_points", 500),
            comment="TradingView"
        )

    run_actions(signal, extra)

    return jsonify({"status": "ok", "signal": action})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"})


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    cfg = load_config()
    executor.initialize()

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    logger.info("Webhook server rodando na porta %d", port)
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
