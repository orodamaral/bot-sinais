import logging
import sys
import os
import winsound
import threading

from .config import load as load_config, save as save_config
from .poller import Poller
from .gui import App

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("main")


def _play_sound():
    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass


def main():
    cfg = load_config()
    server_url = cfg.get("server_url", "https://rodamaral.pythonanywhere.com")

    app = App()

    def on_signal(record):
        app.root.after(0, app.new_signal, record)
        if app.sound_enabled:
            threading.Thread(target=_play_sound, daemon=True).start()

    poller = Poller(server_url, on_signal)

    interval = cfg.get("poll_interval", 2000)

    def poll_loop():
        poller.fetch()
        app.root.after(interval, poll_loop)

    app.root.after(1000, poll_loop)
    app.root.mainloop()


if __name__ == "__main__":
    main()
