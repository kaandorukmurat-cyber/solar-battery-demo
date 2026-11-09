"""Exact mixed-integer version of the dispatch problem (needs scipy >= 1.9, HiGHS).

Used by plan_day when the PPC minimum forces trade-offs: there the fast dynamic
programme's multiplier method can leave a few hundred euros on the table. Two binaries
per interval keep it physical:
  y = importing (no export that interval: a single meter nets import against export)
  z = charging  (a battery charges or discharges, not both)
Returns None if scipy is missing or the solver doesn't finish in time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Settings
from .market import MarketDay

DT = 0.25


def solve_milp(s: Settings, mkt: MarketDay, solar_mw, pay, hard_min: bool, time_limit: float = 30.0):
    try:
        from scipy.optimize import linprog
        from scipy.sparse import lil_matrix
    except ImportError:
        return None
    n = mkt.n
    b, g, c = s.battery, s.grid, s.contract
    eta = np.sqrt(b.round_trip_eff)
    P, X = b.power_mw * DT, g.export_mw * DT
    I = g.import_mw * DT if c.allow_grid_resale else 0.0
    S = np.asarray(solar_mw) * DT
    buy = mkt.purchase_price + g.import_extra_eur
    sell = pay - g.export_fee_eur
    # variables: s2p, sc, gc, bd, cur, soc, y, z  (each n)  + shortfall slack
    K = 8
    N = K * n + 1
    SH = K * n
    ix = lambda k: np.arange(n) + k * n                     # noqa: E731
    cost = np.zeros(N)
    cost[ix(0)] = -sell
    cost[ix(3)] = -sell + b.wear_eur_per_mwh
    cost[ix(2)] = buy
    want_min = c.min_daily_mwh > 0
    cost[SH] = 0 if hard_min else c.shortfall_penalty

    Aeq = lil_matrix((2 * n, N)); beq = np.zeros(2 * n)
    Aub = lil_matrix((4 * n + 1, N)); bub = np.zeros(4 * n + 1)
    for t in range(n):
        Aeq[t, [t, n + t, 4 * n + t]] = 1; beq[t] = S[t]              # solar split
        r = n + t                                                       # battery balance
        Aeq[r, 5 * n + t] = 1; Aeq[r, n + t] = -eta; Aeq[r, 2 * n + t] = -eta; Aeq[r, 3 * n + t] = 1 / eta
        if t:
            Aeq[r, 5 * n + t - 1] = -1
        else:
            beq[r] = b.start_mwh
        k = 4 * t
        Aub[k, 2 * n + t] = 1; Aub[k, 6 * n + t] = -I                   # import only in import mode
        Aub[k + 1, [t, 3 * n + t]] = 1; Aub[k + 1, 6 * n + t] = X; bub[k + 1] = X
        Aub[k + 2, [n + t, 2 * n + t]] = 1; Aub[k + 2, 7 * n + t] = -P  # charge only in charge mode
        Aub[k + 3, 3 * n + t] = 1; Aub[k + 3, 7 * n + t] = P; bub[k + 3] = P
    last = 4 * n                                                        # minimum: -(delivered) - slack <= -min
    if want_min:
        Aub[last, ix(0)] = -1; Aub[last, ix(3)] = -1
        if not c.grid_counts_toward_min:
            Aub[last, ix(2)] = 1
        Aub[last, SH] = -1; bub[last] = -c.min_daily_mwh

    lo = np.zeros(N); hi = np.full(N, np.inf)
    hi[ix(2)] = I; hi[ix(3)] = P
    soc_lo = min(b.min_mwh, b.start_mwh)
    lo[ix(5)] = soc_lo; hi[ix(5)] = b.usable_mwh
    lo[5 * n + n - 1] = max(soc_lo, b.end_min_mwh)
    hi[ix(6)] = 1; hi[ix(7)] = 1
    hi[SH] = 0 if (hard_min or not want_min) else np.inf
    integ = np.zeros(N); integ[6 * n:8 * n] = 1
    res = linprog(cost, A_ub=Aub.tocsr(), b_ub=bub, A_eq=Aeq.tocsr(), b_eq=beq, bounds=list(zip(lo, hi)),
                  method="highs", integrality=integ, options={"time_limit": time_limit, "mip_rel_gap": 1e-4})
    if res.x is None or res.status not in (0, 1):     # 1 = time limit, keep the best found if any
        return None
    x = res.x
    s2p, sc, gc, bd, cur, soc = (x[ix(k)] for k in range(6))
    soc_start = np.r_[b.start_mwh, soc[:-1]]
    exp = s2p + bd
    counted = exp - (0.0 if c.grid_counts_toward_min else gc)
    df = pd.DataFrame({
        "margin": exp * sell - gc * buy - b.wear_eur_per_mwh * bd,
        "exp": exp, "solar_exp": s2p, "batt_exp": bd, "from_sol": sc, "from_grid": gc,
        "dis": bd, "curtail": cur, "counted": counted, "d": soc - soc_start,
        "soc_start": soc_start, "soc_end": soc,
    }, index=mkt.index).clip(lower=-1e12)
    for col in ("exp", "solar_exp", "batt_exp", "from_sol", "from_grid", "dis", "curtail"):
        df[col] = df[col].clip(lower=0)
    return df, res.status == 0
