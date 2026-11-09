"""Inputs for one delivery day (demo build: no live data fetching)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def day_index(day: dt.date, tz: str, minutes: int = 15) -> pd.DatetimeIndex:
    """Interval start times for a local delivery day (92 or 100 intervals on DST days)."""
    start = pd.Timestamp(day, tz=tz)
    end = pd.Timestamp(day + dt.timedelta(days=1), tz=tz)
    return pd.date_range(start, end, freq=f"{minutes}min", inclusive="left")


@dataclass
class MarketDay:
    index: pd.DatetimeIndex
    ro_price: np.ndarray
    neighbours: dict = field(default_factory=dict)
    net_import_mw: np.ndarray | None = None
    solar_mw: np.ndarray | None = None
    solar_low_mw: np.ndarray | None = None
    sources: list = field(default_factory=list)
    buy_price: np.ndarray | None = None
    solar_runs: dict = field(default_factory=dict)

    @property
    def purchase_price(self) -> np.ndarray:
        return self.ro_price if self.buy_price is None else self.buy_price

    @property
    def n(self) -> int:
        return len(self.index)
