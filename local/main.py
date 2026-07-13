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


def _press_hotkey(hotkey: str, target_window: str = ""):
    if not hotkey:
        return
    try:
        import pyautogui
        pyautogui.PAUSE = 0.05
        _focus_window(target_window)
        keys = hotkey.split("+")
        pyautogui.hotkey(*keys, interval=0.08)
        logger.info("Hotkey executado: %s", hotkey)
    except ImportError:
        logger.warning("pyautogui nao instalado. pip install pyautogui")
    except Exception as e:
        logger.error("Erro hotkey %s: %s", hotkey, e)


def main():
    cfg = load_config()
    server_url = cfg.get("server_url", "https://rodamaral.pythonanywhere.com")

    app = App()

    def on_signal(record):
        app.root.after(0, app.new_signal, record)
        if app.sound_enabled:
            threading.Thread(target=_play_sound, daemon=True).start()
        action = record.get("action", "")
        hotkey = app.get_hotkey(action)
        if hotkey:
            target = app.get_window_title()
            threading.Thread(target=_press_hotkey, args=(hotkey, target), daemon=True).start()

    poller = Poller(server_url, on_signal)

    interval = cfg.get("poll_interval", 2000)

    def poll_loop():
        poller.fetch()
        app.root.after(interval, poll_loop)

    app.root.after(1000, poll_loop)
    app.root.mainloop()


if __name__ == "__main__":
    main()
