import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULT = {
    "server_url": "https://rodamaral.pythonanywhere.com",
    "poll_interval": 2000,
    "play_sound": True,
    "sound_file": "",
    "target_window": "",
    "hotkeys": {
        "COMPRA": "",
        "VENDA": "",
        "TAKE": "",
        "STOP LOSS": "",
        "VIRADA DE MÃO": "",
    },
    "click_positions": {},
}


def load():
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT, **data}
        except Exception:
            pass
    return dict(DEFAULT)


def save(data: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged = {**DEFAULT, **data}
    CONFIG_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
