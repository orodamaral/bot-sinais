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

    signal_str = data.get("signal", data.get("Sinal", "NEUTRAL")).upper()
    signal_map = {
        "STRONG BUY": 2,
        "BUY": 1,
        "SELL": -1,
        "STRONG SELL": -2,
        "NEUTRAL": 0,
    }
    signal = signal_map.get(signal_str, 0)

    if signal == 0:
        return jsonify({"status": "ignored", "signal": signal_str})

    extra = {
        "symbol": data.get("symbol") or data.get("ticker") or data.get("Symbol") or data.get("Ticker") or "BTCUSD",
        "price": data.get("price") or data.get("close") or data.get("Price") or data.get("Close") or "0",
        "timeframe": data.get("timeframe") or data.get("Timeframe") or "",
    }

    cfg = load_config()
    trade_cfg = cfg.get("trade", {})
    executor.send_signal(
        signal,
        trade_cfg.get("sl_points", 500),
        trade_cfg.get("tp_points", 500),
        comment="TradingView"
    )

    run_actions(signal, extra)

    return jsonify({"status": "ok", "signal": signal})


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
