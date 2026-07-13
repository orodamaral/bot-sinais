import logging
import threading
from datetime import datetime, timezone, timedelta

from .config import load_config

logger = logging.getLogger("actions")

HOTKEYS = {2: "ctrl+shift+alt+c", -2: "ctrl+shift+alt+v"}

FOOTER = "\nNÃO SEJAM CRACKUDOS! BATEU A META VAZA!"

TEMPLATES = {
    "COMPRA": (
        "🚨🚨🚨ATENÇÃO MEUS AMORES🚨🚨🚨\n"
        "📊 ATIVO: {ticker}\n"
        "⏰ HORÁRIO: {time}\n"
        "💵 PREÇO:  {price}\n"
        "🟢 POSIÇÃO: {action}"
    ),
    "VENDA": (
        "🚨🚨🚨ATENÇÃO MEUS AMORES🚨🚨🚨\n"
        "📊 ATIVO: {ticker}\n"
        "⏰ HORÁRIO: {time}\n"
        "💵 PREÇO:  {price}\n"
        "🔴 POSIÇÃO: {action}"
    ),
    "VIRADA DE MÃO": (
        "🚨🚨🚨ATENÇÃO MEUS AMORES🚨🚨🚨\n"
        "📊 ATIVO: {ticker}\n"
        "⏰ HORÁRIO: {time}\n"
        "💵 PREÇO:  {price}\n"
        "🔄 POSIÇÃO: {action}"
    ),
    "TAKE": (
        "🚨🚨🚨ATENÇÃO MEUS AMORES🚨🚨🚨\n"
        "📊 ATIVO: {ticker}\n"
        "⏰ HORÁRIO: {time}\n"
        "💵 PREÇO:  {price}\n"
        "✅ {action}"
    ),
    "STOP LOSS": (
        "🚨🚨🚨ATENÇÃO MEUS AMORES🚨🚨🚨\n"
        "📊 ATIVO: {ticker}\n"
        "⏰ HORÁRIO: {time}\n"
        "💵 PREÇO:  {price}\n"
        "❌ {action}"
    ),
}


def _fmt_time(time_ms):
    if not time_ms:
        return "-"
    try:
        t = datetime.fromtimestamp(time_ms / 1000, tz=timezone(timedelta(hours=-3)))
        return t.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(time_ms)


def fmt_msg(signal: int, extra: dict = None) -> str:
    xt = extra or {}
    action = xt.get("action", "DESCONHECIDO")
    ticker = xt.get("ticker", "XAUUSD")
    price = xt.get("price", 0)
    time_str = _fmt_time(xt.get("time"))

    template = TEMPLATES.get(action)
    if template:
        body = template.format(ticker=ticker, time=time_str, price=price, action=action)
    else:
        body = f"SINAL: {action}\n{xt.get('ticker', '?')} @ {price}"
    return body + FOOTER


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
        sig_name = (extra or {}).get("action", "?")
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
        logger.info("WhatsApp enviado: %s", "ok")
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
        logger.info("Hotkey executado: %s", hotkey)
    except ImportError:
        logger.warning("pyautogui nao instalado. pip install pyautogui")
    except Exception as e:
        logger.error("Erro hotkey: %s", e)


def run_actions(signal: int, extra: dict = None):
    press_hotkey(signal)
    threading.Thread(target=send_telegram, args=(signal, extra), daemon=True).start()
    threading.Thread(target=send_whatsapp, args=(signal, extra), daemon=True).start()
