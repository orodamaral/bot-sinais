import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class MacroState:
    us10y_slope: float = 0.0
    dxy_slope: float = 0.0
    eur_slope: float = 0.0
    jpy_slope: float = 0.0
    wti_slope: float = 0.0

    us10y_up: bool = False
    dxy_up: bool = False
    eur_up: bool = False
    jpy_up: bool = False
    wti_up: bool = False

    macro_bullish: bool = False
    macro_bearish: bool = False
    dxy_confirms: bool = False
    eur_confirms: bool = False
    jpy_aligns: bool = False
    wti_aligns: bool = False
    macro_score: int = 0


def linreg_slope(values: np.ndarray) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x = np.arange(n)
    y = values
    slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (
        n * np.sum(x ** 2) - np.sum(x) ** 2
    )
    return slope


def norm_slope(values: np.ndarray) -> float:
    s = linreg_slope(values)
    current = values[-1] if len(values) > 0 else 0
    return (s / current * 100) if current != 0 else 0.0


def analyze_macro(
    us10y_close: np.ndarray,
    dxy_close: np.ndarray,
    eur_close: np.ndarray,
    jpy_close: np.ndarray,
    wti_close: np.ndarray,
    reg_len: int = 20,
) -> MacroState:
    state = MacroState()

    state.us10y_slope = norm_slope(us10y_close[-reg_len:])
    state.dxy_slope = norm_slope(dxy_close[-reg_len:])
    state.eur_slope = norm_slope(eur_close[-reg_len:])
    state.jpy_slope = norm_slope(jpy_close[-reg_len:])
    state.wti_slope = norm_slope(wti_close[-reg_len:])

    state.us10y_up = state.us10y_slope > 0
    state.dxy_up = state.dxy_slope > 0
    state.eur_up = state.eur_slope > 0
    state.jpy_up = state.jpy_slope > 0
    state.wti_up = state.wti_slope > 0

    state.macro_bullish = not state.us10y_up
    state.macro_bearish = state.us10y_up

    state.dxy_confirms = (
        (state.macro_bullish and not state.dxy_up)
        or (state.macro_bearish and state.dxy_up)
    )
    state.eur_confirms = (
        (state.dxy_up and not state.eur_up)
        or (not state.dxy_up and state.eur_up)
    )
    state.jpy_aligns = (
        (state.macro_bullish and state.jpy_up)
        or (state.macro_bearish and not state.jpy_up)
    )
    state.wti_aligns = (
        (state.us10y_up and state.wti_up)
        or (not state.us10y_up and not state.wti_up)
    )

    score = 0
    if state.dxy_confirms:
        score += 2
    if state.eur_confirms:
        score += 1
    if state.jpy_aligns:
        score += 1
    if state.wti_aligns:
        score += 1
    state.macro_score = score

    return state
