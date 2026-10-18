import statistics
from datetime import datetime

import numpy as np

SYMBOLS = 12


def symbol_sequence(rows: list[tuple[str, int, datetime]], params: dict) -> list[int]:
    """rows: one payer's (destination, amount, local datetime) in order. Symbol = band*4 + new_destination*2 + night."""
    seen: set[str] = set()
    amounts: list[int] = []
    symbols = []
    for destination, amount, moment in rows:
        band = 1
        if amounts:
            median = statistics.median(amounts)
            if amount < params["low_ratio"] * median:
                band = 0
            elif amount > params["high_ratio"] * median:
                band = 2
        is_new = destination not in seen
        is_night = moment.hour >= params["night_start_hour"] or moment.hour < params["night_end_hour"]
        symbols.append(band * 4 + int(is_new) * 2 + int(is_night))
        seen.add(destination)
        amounts.append(amount)
    return symbols


def log_likelihood(pi: np.ndarray, transition: np.ndarray, emission: np.ndarray, symbols: list[int]) -> float:
    """Scaled forward algorithm; the sum of log scale factors is the sequence log-likelihood."""
    alpha = pi * emission[:, symbols[0]]
    total = np.log(alpha.sum())
    alpha = alpha / alpha.sum()
    for symbol in symbols[1:]:
        alpha = (alpha @ transition) * emission[:, symbol]
        scale = alpha.sum()
        total += np.log(scale)
        alpha = alpha / scale
    return float(total)


def anomaly_score(model: dict, symbols: list[int]) -> tuple[float, float] | None:
    """(anomaly in [0, 1], mean log-likelihood per symbol) of the last `window` symbols; None when too short."""
    window = symbols[-model["window"]:]
    if len(window) < model["min_symbols"]:
        return None
    mean_ll = log_likelihood(
        np.array(model["pi"]), np.array(model["transition"]), np.array(model["emission"]), window
    ) / len(window)
    table = model["cdf"]
    return float(np.interp(-mean_ll, table["nll"], table["probability"])), mean_ll
