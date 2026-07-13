import logging
import threading

from .config import load_config

logger = logging.getLogger("actions")

HOTKEYS = {2: "ctrl+shift+alt+c", -2: "ctrl+shift+alt+v"}


def fmt_msg(signal: int, extra: dict = None) -> str:
    xt = extra or {}
    sig_name = xt.get("signal_name", "DESCONHECIDO")
    ticker = xt.get("ticker", "BINANCE:XAUUSD")
    price = xt.get("price", 0)
    side = xt.get("side", "").upper()
    lines = [
        "┌ GOLD MACRO COMPASS",
        f"├ Sinal: {sig_name}",
        f"├ Ativo: {ticker}",
        f"├ Preco: {price}",
    ]
    if side:
        lines.insert(3, f"├ Lado: {side}")
    return "\n".join(lines)


def send_telegram(signal: int, extra: dict = None):
    cfg = load_config().get("telegram", {})
    if not cfg.get("enabled"):
        return
    token = cfg.get("bot_token", "")
    chat_id = cfg.get("chat_id", "")
    if not token or not chat_id:
        logger.warning("Telegram config incompleta")
        return
    text = fmt_msg(signal, extra)
    import requests
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        sig_name = (extra or {}).get("signal_name", "?")
        logger.info("Telegram enviado: %s", sig_name)
    except Exception as e:
        logger.error("Erro Telegram: %s", e)


def send_whatsapp(signal: int, extra: dict = None):
    cfg = load_config().get("whatsapp", {})
    if not cfg.get("enabled"):
        return
    text = fmt_msg(signal, extra)
    try:
        import pywhatkit as kit
        kit.sendwhatmsg_instantly(
            cfg["phone"],
            text,
            wait_time=int(cfg.get("wait_time", 15))
        )
        logger.info("WhatsApp enviado: %s", sig_name)
    except ImportError:
        logger.warning("pywhatkit nao instalado. pip install pywhatkit")
    except Exception as e:
        logger.error("Erro WhatsApp: %s", e)


def press_hotkey(signal: int):
    cfg = load_config().get("hotkeys", {})
    if not cfg.get("enabled"):
        return
    hotkey = HOTKEYS.get(signal)
    if not hotkey:
        return
    try:
        import pyautogui
        keys = hotkey.split("+")
        pyautogui.hotkey(*keys)
        logger.info("Hotkey executado: %s (%s)", hotkey, SIGNAL_MAP.get(signal, ""))
    except ImportError:
        logger.warning("pyautogui nao instalado. pip install pyautogui")
    except Exception as e:
        logger.error("Erro hotkey: %s", e)


def run_actions(signal: int, extra: dict = None):
    press_hotkey(signal)
    threading.Thread(target=send_telegram, args=(signal, extra), daemon=True).start()
    threading.Thread(target=send_whatsapp, args=(signal, extra), daemon=True).start()
