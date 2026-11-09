"""Dispatch optimiser.

Dynamic programming over the battery's stored energy (discretised), one decision per
interval: how much the stored energy changes. For a given change the best way to source
or use it is fixed (cheapest of spilled solar, exportable solar or grid; solar exported
before battery), so the reward of each move is precomputed per interval.

The PPC daily minimum is enforced with a Lagrange multiplier 'lam' (EUR per MWh of
counted delivery): solve(lam=0) is the most valuable plan; if it delivers too little,
the smallest 'lam' that reaches the minimum is found by bisection. With a shortfall
penalty, 'lam' is capped at the penalty: covering a gap never costs more than paying it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import Settings
from .contract import Payout, expected_payout
from .market import MarketDay

DT = 0.25          # hours per interval
EPS = 1e-9


@dataclass
class Plan:
    table: pd.DataFrame        # one row per interval
    lam: float
    status: str                # met-naturally | met-by-plan | shortfall
    delivered_mwh: float       # counted toward the PPC minimum
    shortfall_mwh: float
    penalty_eur: float
    margin_eur: float          # after fees, grid purchases and wear (before penalty)
    cost_of_minimum_eur: float
    end_relaxed: bool
    payout: Payout
    engine: str = "dp"         # which solver produced the final schedule


def _moves(s: Settings, solar_mw, price, pay, lam, step, kc, kd):
    """Energy flows and value for every (interval, move). Shapes (n, K)."""
    b, g, c = s.battery, s.grid, s.contract
    eta = np.sqrt(b.round_trip_eff)
    S = (np.asarray(solar_mw) * DT)[:, None]
    X = g.export_mw * DT
    I = g.import_mw * DT if c.allow_grid_resale else 0.0
    counts = c.grid_counts_toward_min
    v_s = (pay - g.export_fee_eur + lam)[:, None]           # value of 1 MWh exported
    buy = (price + g.import_extra_eur)[:, None]
    c_g = buy + (0.0 if counts else lam)                    # effective cost of 1 MWh imported
    d = (np.arange(-kd, kc + 1) * step)[None, :]            # change in stored energy

    exportable = np.minimum(S, X)
    spill = S - exportable
    charging = d >= 0
    need = np.where(charging, d / eta, 0.0)
    from_spill = np.minimum(spill, need)
    rem = need - from_spill
    # Single meter: importing and exporting in the same interval would net out, so grid
    # energy is only drawn once all solar is going into the battery (no export that interval).
    from_sol = np.minimum(rem, exportable)
    from_grid = np.minimum(rem - from_sol, I)
    unmet = rem - from_sol - from_grid
    dis = np.where(charging, 0.0, -d * eta)

    can_sell = v_s > 0
    exp = np.where(charging, np.where(can_sell, exportable - from_sol, 0.0),
                   np.where(can_sell, np.minimum(S + dis, X), 0.0))
    solar_exp = np.where(charging, exp, np.minimum(S, exp))
    batt_exp = exp - solar_exp
    curtail = np.maximum(0.0, S - from_spill - from_sol - solar_exp)

    # tiny tie-breakers: charge when solar is highest, avoid pointless cycling
    tie = np.where(charging, d * (0.02 * S / DT - 0.01), 0.01 * d)
    obj = exp * v_s - from_grid * c_g - s.battery.wear_eur_per_mwh * dis + tie
    obj = np.where(unmet > 1e-9, -np.inf, obj)
    margin = exp * (pay[:, None] - g.export_fee_eur) - from_grid * buy - s.battery.wear_eur_per_mwh * dis
    counted = exp - (0.0 if counts else from_grid)
    out = dict(obj=obj, margin=margin, exp=exp, solar_exp=solar_exp, batt_exp=batt_exp,
               from_sol=from_sol + from_spill, from_grid=from_grid, dis=dis, curtail=curtail,
               counted=counted, d=d)
    return {k: np.broadcast_to(v, obj.shape) for k, v in out.items()}


def solve(s: Settings, mkt: MarketDay, solar_mw: np.ndarray, pay: np.ndarray, lam: float, levels: int = 400):
    b = s.battery
    cap = max(1e-3, b.usable_mwh)
    N = int(np.clip(round(cap / 0.05), 50, levels))
    step = cap / N
    eta = np.sqrt(b.round_trip_eff)
    kc = int(np.floor(b.power_mw * DT * eta / step + EPS))
    kd = int(np.floor(b.power_mw * DT / eta / step + EPS))
    K = kc + kd + 1
    n = mkt.n
    mv = _moves(s, solar_mw, mkt.purchase_price, pay, lam, step, kc, kd)
    R = mv["obj"]

    min_s = min(N, int(np.ceil(b.min_mwh / step - EPS)))
    end_s = min(N, int(np.ceil(b.end_min_mwh / step - EPS)))
    s0 = int(np.clip(round(b.start_mwh / step), 0, N))
    end_relaxed = False
    if end_s > min(N, s0 + kc * n):
        end_s, end_relaxed = min(N, s0 + kc * n), True

    states = np.arange(N + 1)
    moves = np.arange(K) - kd
    nxt = states[None, :] + moves[:, None]                    # (K, N+1) next state
    valid = (nxt >= 0) & (nxt <= N)
    valid &= ~((nxt < min_s) & (moves[:, None] < 0))          # no discharge below reserve
    nxt_c = np.clip(nxt, 0, N)

    def backward(end_level):
        V = np.full(N + 1, -np.inf)
        V[states >= end_level] = 0.0
        choice = np.zeros((n, N + 1), dtype=np.int32)
        for t in range(n - 1, -1, -1):
            cand = R[t][:, None] + V[nxt_c]
            cand[~valid] = -np.inf
            j = np.argmax(cand, axis=0)
            choice[t] = j
            V = cand[j, states]
        return V, choice

    V, choice = backward(max(end_s, min(min_s, s0)))
    if not np.isfinite(V[s0]):
        # end-of-day target unreachable (e.g. no sun and no grid charging): drop it.
        # Holding is always allowed, so this always has a valid path.
        end_relaxed = True
        V, choice = backward(0)
    rows, st = [], s0
    for t in range(n):
        j = choice[t, st]
        rows.append({k: float(v[t, j]) for k, v in mv.items() if k != "obj"} | {"soc_start": st * step})
        st = int(st + j - kd)
        rows[-1]["soc_end"] = st * step
    return pd.DataFrame(rows, index=mkt.index), end_relaxed


def plan_day(s: Settings, mkt: MarketDay, solar_mw: np.ndarray | None = None, solver: str = "auto") -> Plan:
    """solver: "dp" = fast dynamic programme only; "auto" = DP, refined by the exact MILP when
    the PPC minimum forces trade-offs; "exact" = always solve with the MILP (falls back to DP)."""
    solar_mw = mkt.solar_mw if solar_mw is None else solar_mw
    po = expected_payout(mkt, s)
    c = s.contract
    target = c.min_daily_mwh

    base, relaxed = solve(s, mkt, solar_mw, po.expected, 0.0)
    df, lam, status, engine = base, 0.0, "met-naturally", "dp"
    if target > 0 and base.counted.sum() < target - 1e-6:
        lmax = c.shortfall_penalty if c.shortfall_penalty > 0 else 20000.0
        hi_df, relaxed = solve(s, mkt, solar_mw, po.expected, lmax)
        if hi_df.counted.sum() < target - 1e-6:
            df, lam, status = hi_df, lmax, "shortfall"
        else:
            lo, hi, best = 0.0, lmax, hi_df
            for _ in range(22):
                mid = (lo + hi) / 2
                cand, r = solve(s, mkt, solar_mw, po.expected, mid)
                if cand.counted.sum() >= target - 1e-6:
                    hi, best, relaxed = mid, cand, r
                else:
                    lo = mid
            df, lam, status = best, hi, "met-by-plan"

    def score(t):  # margin net of any shortfall penalty
        return t.margin.sum() - max(0.0, target - t.counted.sum()) * c.shortfall_penalty

    use_exact = solver == "exact" or (solver == "auto" and (
        status == "met-by-plan" or (status == "shortfall" and c.shortfall_penalty > 0)))
    if use_exact and not relaxed:
        from .milp import solve_milp
        hard = c.shortfall_penalty <= 0
        out = solve_milp(s, mkt, solar_mw, po.expected, hard_min=hard)
        if out is not None:
            mdf, _optimal = out
            if score(mdf) > score(df) + 1e-6:
                df, engine = mdf, "milp"

    df = _finish_table(df, mkt, solar_mw, po)
    delivered = float(df.counted.sum())
    short = max(0.0, target - delivered)
    if target > 0 and status != "met-naturally":
        status = "shortfall" if short > 1e-6 else "met-by-plan"
    plan = Plan(table=df, lam=lam, status=status, delivered_mwh=delivered, shortfall_mwh=short,
                penalty_eur=short * c.shortfall_penalty, margin_eur=float(df.margin.sum()),
                cost_of_minimum_eur=float(base.margin.sum() - df.margin.sum()), end_relaxed=relaxed, payout=po)
    plan.engine = engine
    return plan


ACTIONS = {
    "buy": "Buy & charge",
    "charge_solar": "Charge from solar",
    "discharge_surge": "Discharge to PPC (surge)",
    "discharge": "Discharge to PPC",
    "sell": "Sell solar to PPC",
    "hold": "Hold",
}


def _action(r, surge_p) -> str:
    # moves under 0.05 MWh per interval are rounding residue, not actions
    if r.from_grid > 0.05:
        return "buy"
    if r.from_sol > 0.05:
        return "charge_solar"
    if r.dis > 0.05:
        return "discharge_surge" if surge_p >= 0.5 else "discharge"
    if r.solar_exp > 1e-4:
        return "sell"
    return "hold"


def _finish_table(df: pd.DataFrame, mkt: MarketDay, solar_mw, po: Payout) -> pd.DataFrame:
    df = df.copy()
    df["solar_mw"] = solar_mw
    df["ro_price"] = mkt.ro_price
    df["surge_prob"] = po.surge_prob
    df["expected_payout"] = po.expected
    df["action"] = [_action(r, p) for r, p in zip(df.itertuples(), po.surge_prob)]
    return df
