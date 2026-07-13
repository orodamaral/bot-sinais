import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "settings.json"

DEFAULT_CONFIG = {
    "macro": {
        "regression_length": 20,
        "macro_timeframe_mins": 60,
        "us10y_symbol": "US10Y",
        "dxy_symbol": "DXY",
        "eurusd_symbol": "EURUSD",
        "usdjpy_symbol": "USDJPY",
        "wti_symbol": "USOIL",
        "xauusd_symbol": "XAUUSD"
    },
    "technical": {
        "rsi_period": 7,
        "rsi_overbought": 80,
        "rsi_oversold": 20,
        "ema_fast": 9,
        "ema_slow": 21
    },
    "trade": {
        "sl_points": 500,
        "tp_points": 500,
        "max_spread": 50,
        "max_daily_loss": 1000,
        "max_concurrent_trades": 1,
        "min_macro_score": 3
    },
    "mt4": {
        "path": "C:\\Program Files\\MetaTrader 4\\terminal64.exe",
        "account": 0,
        "password": "",
        "server": ""
    },
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": ""
    },
    "whatsapp": {
        "enabled": False,
        "phone": "",
        "wait_time": 15
    },
    "hotkeys": {
        "enabled": False
    },
    "mode": "webhook",
    "log_level": "INFO"
}


def load_config():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
