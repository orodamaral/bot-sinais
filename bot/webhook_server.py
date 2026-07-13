import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

from flask import Flask, request, jsonify

from .config import load_config
from .mt4_executor import MT4Executor
from .actions import run_actions

logger = logging.getLogger("webhook_server")
app = Flask(__name__)
executor = MT4Executor()
executor.initialize()

DATA_DIR = Path(__file__).parent.parent / "data"
LAST_SIGNAL_FILE = DATA_DIR / "last_signal.json"
HISTORY_FILE = DATA_DIR / "signal_history.json"
MAX_HISTORY = 1000


def _save_signal(data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAST_SIGNAL_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append(data)
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def _fmt_time_br(time_ms):
    try:
        t = datetime.fromtimestamp(time_ms / 1000, tz=timezone(timedelta(hours=-3)))
        return t.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(time_ms)


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

    record = {
        "ticker": ticker,
        "action": action,
        "price": price,
        "time": time_ms,
        "time_str": _fmt_time_br(time_ms),
    }

    _save_signal(record)

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


@app.route("/last_signal", methods=["GET"])
def last_signal():
    if LAST_SIGNAL_FILE.exists():
        try:
            return jsonify(json.loads(LAST_SIGNAL_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return jsonify({"status": "no_signal"})


@app.route("/history", methods=["GET"])
def history():
    limit = request.args.get("limit", 100, type=int)
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            return jsonify(data[-limit:])
        except Exception:
            pass
    return jsonify([])


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
