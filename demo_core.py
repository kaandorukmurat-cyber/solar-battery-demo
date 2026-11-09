"""Calculations behind the Solar + Battery demo (no user interface here).

Uses the real day-ahead planner in ./dayahead to plan one day, and compares it with
"solar only" and a simple fixed battery timetable on the same day and contract.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from dayahead.config import Settings
from dayahead.market import MarketDay, day_index
from dayahead.optimizer import DT, plan_day

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "demo_data.json").read_text(encoding="utf-8"))
SCENARIOS = {s["key"]: s for s in DATA["scenarios"]}
TZ = "Europe/Bucharest"
BATTERIES = [0, 10, 20, 40]
# Standard battery used by the full-year results; every value can be overridden for the One day view.
STANDARD_SPECS = dict(duration_h=2.0, rte_pct=88.0, wear=15.0, reserve_pct=5.0, start_pct=20.0, end_pct=20.0)


def settings(battery_mwh: float, pay_rule: str = "market", fixed_price: float = 305.0,
             peak: bool = False, peak_price: float = 305.0, min_mwh: float = 0.0,
             penalty: float = 50.0, specs: dict | None = None) -> Settings:
    """Demo site: 30 MWp / 26 MW, battery (standard 2-hour unless specs given), PPC contract as chosen."""
    sp = {**STANDARD_SPECS, **(specs or {})}
    s = Settings()
    s.site.latitude, s.site.longitude = 44.32, 23.80
    s.site.dc_mwp, s.site.ac_mw = 30.0, 26.0
    s.grid.export_mw = s.grid.import_mw = 26.0
    b = s.battery
    b.usable_mwh = max(battery_mwh, 0.01)
    b.power_mw = max(battery_mwh / max(float(sp["duration_h"]), 0.25), 0.01)
    b.start_mwh = sp["start_pct"] / 100 * battery_mwh
    b.end_min_mwh = sp["end_pct"] / 100 * battery_mwh
    b.min_mwh = min(sp["reserve_pct"], sp["start_pct"], sp["end_pct"]) / 100 * battery_mwh
    b.round_trip_eff, b.wear_eur_per_mwh = sp["rte_pct"] / 100, float(sp["wear"])
    c = s.contract
    if pay_rule == "market":                       # PPC pays the day-ahead price every hour
        c.normal_rule, c.normal_value = "pct", 100.0
    else:
        c.normal_rule, c.normal_value = "fixed", float(fixed_price)
    c.surge_windows = ["17:00-22:00"]
    if peak:                                       # a fixed evening price (not agreed yet)
        c.surge_rule, c.surge_value = "fixed", float(peak_price)
    else:                                          # no peak agreement: evening paid like any hour
        c.surge_rule, c.surge_value = c.normal_rule, c.normal_value
    c.allow_grid_resale, c.grid_counts_toward_min = True, False
    c.min_daily_mwh, c.shortfall_penalty = float(min_mwh), float(penalty)
    s.signals.enabled = False
    return s


def scenario_prices(sc: dict, day_average: float | None = None) -> np.ndarray:
    p = np.asarray(sc["prices"], dtype=float)
    if sc["key"] == "live" and day_average:        # tomorrow's prices are modelled: scale to the chosen average
        p = p * day_average / p.mean()
    return p


def _execute(s: Settings, rows, sun, prices, pay) -> dict:
    """Run battery actions against the day's sun and money (same rules as the business-case model)."""
    b, g, c = s.battery, s.grid, s.contract
    eta = np.sqrt(b.round_trip_eff)
    soc, deliv, margin, dis_sum = b.start_mwh, 0.0, 0.0, 0.0
    for t, (sc_p, gc_p, dis_p) in enumerate(rows):
        S = sun[t] * DT
        room = (b.usable_mwh - soc) / eta
        sc = min(sc_p, S, room)
        gc = min(gc_p, max(0.0, room - sc))
        dis = min(dis_p, max(0.0, (soc - min(b.min_mwh, soc)) * eta))
        soc += (sc + gc) * eta - dis / eta
        exp = 0.0 if gc > 1e-9 else min(S - sc + dis, g.export_mw * DT)
        deliv += exp - (0.0 if c.grid_counts_toward_min else gc)
        margin += exp * (pay[t] - g.export_fee_eur) - gc * (prices[t] + g.import_extra_eur) - b.wear_eur_per_mwh * dis
        dis_sum += dis
    short = max(0.0, c.min_daily_mwh - deliv)
    return dict(margin=margin - c.shortfall_penalty * short, delivered=deliv, short=short,
                penalty=c.shortfall_penalty * short, discharged=dis_sum)


def _simple_rule(s: Settings, idx: pd.DatetimeIndex, sun, prices, pay) -> dict:
    """Fixed timetable: charge from solar 11:00-15:00, discharge evenly 18:00-22:00."""
    b = s.battery
    eta = np.sqrt(b.round_trip_eff)
    h = (idx.hour + idx.minute / 60).values
    n_dis = int(((h >= 18) & (h < 22)).sum())
    per = min(b.power_mw * DT, (b.usable_mwh - b.end_min_mwh) * eta / max(n_dis, 1))
    rows, soc = [], b.start_mwh
    for t in range(len(idx)):
        S = sun[t] * DT
        if 11 <= h[t] < 15:
            ch = min(b.power_mw * DT, S, (b.usable_mwh - soc) / eta)
            soc += ch * eta
            rows.append((ch, 0.0, 0.0))
        elif 18 <= h[t] < 22:
            dis = min(per, max(0.0, soc - b.end_min_mwh) * eta)
            soc -= dis / eta
            rows.append((0.0, 0.0, dis))
        else:
            rows.append((0.0, 0.0, 0.0))
    return _execute(s, rows, sun, prices, pay)


def run_day(key: str, battery_mwh: float = 0, pay_rule: str = "market", fixed_price: float = 305.0,
            peak: bool = False, peak_price: float = 305.0, min_mwh: float | None = None,
            penalty: float = 50.0, day_average: float | None = 305.0, specs: dict | None = None) -> dict:
    """Plan one demo day. Returns totals for the three strategies and a 15-minute table."""
    sc = SCENARIOS[key]
    idx = day_index(dt.date.fromisoformat(sc["date"]), TZ)
    prices = scenario_prices(sc, day_average)
    sun = np.asarray(sc["solar"], dtype=float)
    mn = sc["min"] if min_mwh is None else min_mwh
    mkt = MarketDay(index=idx, ro_price=prices, solar_mw=sun, solar_low_mw=sun * 0.8)

    s0 = settings(0, pay_rule, fixed_price, peak, peak_price, mn, penalty)
    s0.battery.start_mwh = s0.battery.end_min_mwh = s0.battery.min_mwh = 0.0
    p0 = plan_day(s0, mkt, solver="dp")
    pay = p0.payout.expected
    rows0 = list(zip(p0.table.from_sol, p0.table.from_grid, p0.table.dis))
    solo = _execute(s0, rows0, sun, prices, pay)

    if battery_mwh > 0:
        s = settings(battery_mwh, pay_rule, fixed_price, peak, peak_price, mn, penalty, specs)
        rule = _simple_rule(s, idx, sun, prices, pay)
        plan = plan_day(s, mkt, solver="auto")
        rows = list(zip(plan.table.from_sol, plan.table.from_grid, plan.table.dis))
        planner = _execute(s, rows, sun, prices, pay)
        t = plan.table
    else:
        rule, planner, t = None, solo, p0.table

    times = [ts.strftime("%H:%M") for ts in idx]
    table = pd.DataFrame({
        "time": times,
        "solar_mw": sun,
        "solar_to_ppc_mw": t.solar_exp.values * 4,
        "battery_to_ppc_mw": t.batt_exp.values * 4,
        "solar_to_battery_mw": -t.from_sol.values * 4,
        "grid_to_battery_mw": -t.from_grid.values * 4,
        "curtailed_mw": t.curtail.values * 4,
        "battery_mwh": t.soc_end.values,
        "market_eur_mwh": prices,
        "ppc_pays_eur_mwh": pay,
    })
    return dict(scenario=sc, solar_mwh=float(sun.sum() * DT), min_mwh=float(mn),
                price_min=float(prices.min()), price_max=float(prices.max()),
                solar_only=solo, simple_rule=rule, planner=planner,
                stored_mwh=float(t.from_sol.sum()), bought_mwh=float(t.from_grid.sum()),
                sold_from_battery_mwh=float(t.dis.sum()), table=table)


def year(battery_mwh: int, price_year: str = "2026") -> dict:
    """Pre-computed modelled year (today's contract: PPC pays the day-ahead price every hour)."""
    return DATA["year"][f"{int(battery_mwh)}|{price_year}"]
