"""PPC payout per interval: normal rule, surge rule and how likely a surge is."""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import Settings
from .market import MarketDay


def pay_rule(rule: str, value: float, price: np.ndarray) -> np.ndarray:
    """fixed: value EUR/MWh | pct: value % of OPCOM | plus: OPCOM + value EUR/MWh"""
    if rule == "fixed":
        return np.full_like(price, value, dtype=float)
    if rule == "pct":
        return price * value / 100.0
    if rule == "plus":
        return price + value
    raise ValueError(f"Unknown payout rule '{rule}' (use fixed, pct or plus)")


def parse_windows(windows: list[str] | str) -> list[tuple[float, float]]:
    """'17:00-22:00' -> [(17.0, 22.0)]; windows crossing midnight are split."""
    if isinstance(windows, str):
        windows = re.split(r"[,;]", windows)
    out = []
    for w in windows:
        m = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*", w)
        if not m:
            if w.strip():
                raise ValueError(f"Can't read surge window '{w}' (expected HH:MM-HH:MM)")
            continue
        a = int(m[1]) + int(m[2] or 0) / 60
        b = int(m[3]) + int(m[4] or 0) / 60
        if b > a:
            out.append((a, b))
        elif b < a:
            out += [(a, 24.0), (0.0, b)]
    return out


@dataclass
class Payout:
    expected: np.ndarray      # EUR/MWh expected from PPC per interval
    surge_prob: np.ndarray    # 0..1
    reason: list[str]


def expected_payout(mkt: MarketDay, s: Settings) -> Payout:
    c, sig = s.contract, s.signals
    idx: pd.DatetimeIndex = mkt.index
    clock = idx.hour + idx.minute / 60
    p = np.zeros(mkt.n)
    reason = [""] * mkt.n
    for a, b in parse_windows(c.surge_windows):
        inside = (clock >= a) & (clock < b)
        p[inside] = 1.0
        for i in np.flatnonzero(inside):
            reason[i] = "contract window"

    if sig.enabled and sig.weight > 0:
        ro = mkt.ro_price
        score = 1 / (1 + np.exp(-(ro - sig.price_threshold) / 15))
        if mkt.neighbours:
            nb = np.max(np.vstack(list(mkt.neighbours.values())), axis=0)
            score += np.where(ro - nb > 5, 0.2, 0.0)          # RO decoupled upward = scarcity
        if mkt.net_import_mw is not None:
            score += np.where(mkt.net_import_mw > sig.net_import_threshold_mw, 0.2, 0.0)
        score = np.minimum(score, 0.95) * sig.weight
        score[score < 0.03] = 0.0                              # ignore noise
        for i in np.flatnonzero(score > p):
            reason[i] = "market signals"
        p = np.maximum(p, score)

    normal = pay_rule(c.normal_rule, c.normal_value, mkt.ro_price)
    surge = pay_rule(c.surge_rule, c.surge_value, mkt.ro_price)
    return Payout(expected=normal + p * (surge - normal), surge_prob=p, reason=reason)
