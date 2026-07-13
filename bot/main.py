import argparse
import json
import logging
import time
import sys
from pathlib import Path
from datetime import datetime

import numpy as np

from .config import load_config
from .macro_logic import analyze_macro
from .signal_engine import analyze_signal, SignalResult
from .mt4_executor import MT4Executor

logger = logging.getLogger("gold_macro_bot")


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                Path(__file__).parent.parent / "data" / "bot.log",
                mode="a"
            )
        ]
    )


def fetch_data_from_mt4(executor: MT4Executor, symbol: str, bars: int,
                        timeframe_mins: int) -> np.ndarray:
    try:
        import MetaTrader4 as mt4
        timeframe_map = {
            1: mt4.TIMEFRAME_M1,
            5: mt4.TIMEFRAME_M5,
            15: mt4.TIMEFRAME_M15,
            30: mt4.TIMEFRAME_M30,
            60: mt4.TIMEFRAME_H1,
            240: mt4.TIMEFRAME_H4,
            1440: mt4.TIMEFRAME_D1,
        }
        tf = timeframe_map.get(timeframe_mins, mt4.TIMEFRAME_H1)
        rates = mt4.copy_rates_from_pos(symbol, tf, 0, bars)
        if rates is None or len(rates) == 0:
            logger.warning("Sem dados para %s no timeframe %d", symbol, timeframe_mins)
            return np.array([])
        return np.array([r[4] for r in rates])
    except Exception as e:
        logger.error("Erro ao buscar dados do MT4: %s", e)
        return np.array([])


def _yf_period(interval: str) -> str:
    if interval == "1m":
        return "5d"
    if interval in ("5m", "15m", "30m", "1h"):
        return "1mo"
    return "6mo"


def fetch_data_from_yfinance(symbol: str, bars: int, interval: str = "1h") -> np.ndarray:
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=_yf_period(interval), interval=interval)
        if df.empty:
            logger.warning("Sem dados yfinance para %s", symbol)
            return np.array([])
        closes = df["Close"].values
        return closes[-bars:] if len(closes) >= bars else closes
    except ImportError:
        logger.warning("yfinance nao instalado")
        return np.array([])
    except Exception as e:
        logger.error("Erro yfinance %s: %s", symbol, e)
        return np.array([])


def run_cycle(executor: MT4Executor, cfg: dict) -> SignalResult:
    macro_cfg = cfg["macro"]
    tech_cfg = cfg["technical"]
    trade_cfg = cfg["trade"]

    bars_needed = max(
        macro_cfg["regression_length"] + 10,
        tech_cfg["ema_slow"] + 5,
        tech_cfg["rsi_period"] + 5
    )
    tf_min = macro_cfg["macro_timeframe_mins"]

    symbol_map = {
        "us10y": macro_cfg["us10y_symbol"],
        "dxy": macro_cfg["dxy_symbol"],
        "eurusd": macro_cfg["eurusd_symbol"],
        "usdjpy": macro_cfg["usdjpy_symbol"],
        "wti": macro_cfg["wti_symbol"],
        "xauusd": macro_cfg["xauusd_symbol"],
    }

    data = {}
    if executor.connected:
        for key, sym in symbol_map.items():
            data[key] = fetch_data_from_mt4(executor, sym, bars_needed, tf_min)
    else:
        yf_map = {
            "us10y": "^TNX",
            "dxy": "DX-Y.NYB",
            "eurusd": "EURUSD=X",
            "jpy": "USDJPY=X",
            "wti": "CL=F",
            "xauusd": "GC=F",
        }
        interval_map = {1: "1m", 5: "5m", 15: "15m", 30: "30m", 60: "1h", 240: "4h", 1440: "1d"}
        interval = interval_map.get(tf_min, "1h")
        for key, sym in yf_map.items():
            data[key] = fetch_data_from_yfinance(sym, bars_needed, interval)

    if any(len(v) < 10 for v in data.values()):
        logger.warning("Dados insuficientes para analise")
        result = SignalResult()
        return result

    macro = analyze_macro(
        data["us10y"], data["dxy"], data["eurusd"],
        data["jpy"], data["wti"],
        reg_len=macro_cfg["regression_length"]
    )

    result = analyze_signal(
        data["xauusd"], macro,
        rsi_period=tech_cfg["rsi_period"],
        rsi_ob=tech_cfg["rsi_overbought"],
        rsi_os=tech_cfg["rsi_oversold"],
        ema_fast=tech_cfg["ema_fast"],
        ema_slow=tech_cfg["ema_slow"],
        min_score=trade_cfg["min_macro_score"]
    )

    logger.info(
        "Signal=%d | Score=%d/5 | RSI=%.1f | MACRO=%s | EMA=%s",
        result.signal, result.macro_score, result.rsi,
        "BULL" if result.macro_bullish else "BEAR",
        "BULL" if result.ema_bullish else "BEAR"
    )

    return result


def run_bot_loop(cfg: dict):
    executor = MT4Executor()
    executor.initialize()

    trade_cfg = cfg["trade"]
    last_signal = 0
    mode = cfg.get("mode", "webhook")

    if mode == "mt4_loop":
        logger.info("Iniciando modo loop MT4 (a cada 60s)...")
        while True:
            try:
                result = run_cycle(executor, cfg)
                if result.signal != 0 and result.signal != last_signal:
                    executor.send_signal(
                        result.signal, trade_cfg["sl_points"],
                        trade_cfg["tp_points"]
                    )
                    last_signal = result.signal
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("Bot interrompido")
                break
            except Exception as e:
                logger.error("Erro no ciclo: %s", e)
                time.sleep(60)
    else:
        logger.info("Modo webhook. Aguardando sinais externos...")

    executor.shutdown()


def run_single(cfg: dict):
    executor = MT4Executor()
    executor.initialize()
    result = run_cycle(executor, cfg)
    executor.shutdown()
    print(json.dumps({
        "signal": result.signal,
        "score": result.macro_score,
        "rsi": round(result.rsi, 1),
        "macro": "BULL" if result.macro_bullish else "BEAR",
        "ema": "BULL" if result.ema_bullish else "BEAR",
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Gold Macro Compass Bot")
    parser.add_argument("--mode", choices=["loop", "once", "webhook"], default="once",
                        help="Modo de operacao")
    parser.add_argument("--log-level", default="INFO", help="Nivel de log")
    args = parser.parse_args()

    setup_logging(args.log_level)
    cfg = load_config()

    if args.mode == "once":
        run_single(cfg)
    elif args.mode == "loop":
        cfg["mode"] = "mt4_loop"
        run_bot_loop(cfg)
    else:
        cfg["mode"] = "webhook"
        run_bot_loop(cfg)


if __name__ == "__main__":
    main()
