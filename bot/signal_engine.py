import numpy as np
from dataclasses import dataclass
from typing import Optional

from .macro_logic import MacroState


SIGNAL_STRONG_SELL = -2
SIGNAL_SELL = -1
SIGNAL_NEUTRAL = 0
SIGNAL_BUY = 1
SIGNAL_STRONG_BUY = 2


@dataclass
class SignalResult:
    signal: int = SIGNAL_NEUTRAL
    macro_score: int = 0
    rsi: float = 50.0
    ema_bullish: bool = False
    macro_bullish: bool = False
    macro_bearish: bool = False


def compute_ema(data: np.ndarray, period: int) -> np.ndarray:
    result = np.copy(data)
    alpha = 2.0 / (period + 1)
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def compute_rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
    deltas = np.diff(data)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    rsi = np.zeros(len(data))
    rsi[:period] = 50.0

    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, len(data)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi


def analyze_signal(
    xau_close: np.ndarray,
    macro: MacroState,
    rsi_period: int = 7,
    rsi_ob: int = 80,
    rsi_os: int = 20,
    ema_fast: int = 9,
    ema_slow: int = 21,
    min_score: int = 3,
) -> SignalResult:
    result = SignalResult()
    result.macro_score = macro.macro_score
    result.macro_bullish = macro.macro_bullish
    result.macro_bearish = macro.macro_bearish

    if len(xau_close) < max(ema_slow, rsi_period) + 5:
        return result

    rsi_values = compute_rsi(xau_close, rsi_period)
    result.rsi = float(rsi_values[-1])

    ema_fast_vals = compute_ema(xau_close, ema_fast)
    ema_slow_vals = compute_ema(xau_close, ema_slow)
    result.ema_bullish = ema_fast_vals[-1] > ema_slow_vals[-1]

    macro_strong = macro.macro_score >= 5
    macro_mod = 3 <= macro.macro_score < 5
    macro_weak = macro.macro_score < 3

    if macro_weak:
        result.signal = SIGNAL_NEUTRAL
        return result

    rsi_not_overbought = result.rsi < rsi_ob
    rsi_not_oversold = result.rsi > rsi_os

    if macro.macro_bullish:
        if macro_strong and rsi_not_overbought and result.ema_bullish:
            result.signal = SIGNAL_STRONG_BUY
        elif macro_mod and rsi_not_overbought:
            result.signal = SIGNAL_BUY
        else:
            result.signal = SIGNAL_NEUTRAL
    elif macro.macro_bearish:
        if macro_strong and rsi_not_oversold and not result.ema_bullish:
            result.signal = SIGNAL_STRONG_SELL
        elif macro_mod and rsi_not_oversold:
            result.signal = SIGNAL_SELL
        else:
            result.signal = SIGNAL_NEUTRAL
    else:
        result.signal = SIGNAL_NEUTRAL

    return result
