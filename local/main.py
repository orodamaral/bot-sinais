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


def _focus_window(title_match: str):
    if not title_match:
        return True
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(title_match)
        if not wins:
            logger.warning("Janela '%s' nao encontrada", title_match)
            return False
        win = wins[0]
        if win.isMinimized:
            win.restore()
        win.activate()
        import time
        time.sleep(0.3)
        return True
    except ImportError:
        logger.debug("pygetwindow nao instalado")
        return False
    except Exception as e:
        logger.debug("Erro ao focar janela: %s", e)
        return False


def _click_position(pos, target_window: str = ""):
    if not pos:
        return
    try:
        import pyautogui
        _focus_window(target_window)
        pyautogui.PAUSE = 0.05
        x, y = pos
        pyautogui.click(x, y)
        logger.info("Clique executado em (%d, %d)", x, y)
    except ImportError:
        logger.warning("pyautogui nao instalado. pip install pyautogui")
    except Exception as e:
        logger.error("Erro clique: %s", e)


def main():
    cfg = load_config()
    server_url = cfg.get("server_url", "https://rodamaral.pythonanywhere.com")

    app = App()

    def on_signal(record):
        app.root.after(0, app.new_signal, record)
        if app.sound_enabled:
            threading.Thread(target=_play_sound, daemon=True).start()
        action = record.get("action", "")
        pos = app.get_click_position(action)
        if pos:
            target = app.get_window_title()
            threading.Thread(target=_click_position, args=(pos, target), daemon=True).start()

    poller = Poller(server_url, on_signal)

    # Sincroniza timestamp inicial para não re-executar sinal antigo
    import requests as _req
    try:
        r = _req.get(f"{server_url}/last_signal", timeout=5)
        if r.status_code == 200:
            d = r.json()
            if d.get("time"):
                poller.set_last_time(d["time"])
    except Exception:
        pass

    interval = cfg.get("poll_interval", 2000)

    def poll_loop():
        poller.fetch()
        app.root.after(interval, poll_loop)

    app.root.after(1000, poll_loop)
    app.root.mainloop()


if __name__ == "__main__":
    main()
