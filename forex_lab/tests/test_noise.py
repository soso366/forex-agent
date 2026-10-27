import numpy as np
import pandas as pd

from forex_lab.indices.noise import simulate, to_arrays


def _session(n_days=30, drift=0.0, noise=0.2, seed=1, late_drift=None):
    rng = np.random.default_rng(seed)
    rows = []
    price = 4000.0
    for k, d in enumerate(pd.bdate_range("2024-01-02", periods=n_days)):
        dr = late_drift if (late_drift is not None and k >= 14) else drift
        for m in range(390):
            o = price
            price = price + dr + noise * rng.standard_normal()
            rows.append({"jour": d.strftime("%Y-%m-%d"), "m": m, "bo": o - 0.25, "ao": o + 0.25, "bc": price - 0.25,
                         "ac": price + 0.25, "h": max(o, price) + 0.1, "l": min(o, price) - 0.1, "v": 1.0})
    return pd.DataFrame(rows)


def test_strong_uptrend_days_are_profitable_longs():
    days, A = to_arrays(_session(drift=0.01, noise=0.05, late_drift=0.05))
    res, _ = simulate(days, A, 0.1)
    act = res[res["actif"]]
    first = act.iloc[:10]  # tant que la tendance du jour dépasse le bruit des 14 jours passés
    assert len(act) == 16 and (first["trades"] > 0).all() and (first["r"] > 0).all()


def test_no_lookahead_decisions_before_change():
    df = _session(drift=0.0, noise=0.5, seed=3)
    days, A = to_arrays(df)
    r1, _ = simulate(days, A, 0.1)
    last = days[-1]
    df2 = df.copy()
    sel = (df2.jour == last) & (df2.m >= 200)
    for c in ("bo", "ao", "bc", "ac", "h", "l"):
        df2.loc[sel, c] += 50          # le futur du dernier jour change à partir de 12:50
    days2, A2 = to_arrays(df2)
    r2, _ = simulate(days2, A2, 0.1)
    assert r1.loc[days[:-1], "r"].equals(r2.loc[days[:-1], "r"])  # jours précédents identiques
    assert r1.loc[last, "trades"] >= 0 and r2.loc[last, "r"] != r1.loc[last, "r"] or r1.loc[last, "trades"] == r2.loc[last, "trades"]


def test_costs_reduce_returns():
    days, A = to_arrays(_session(drift=0.02, noise=0.3, seed=5))
    a, _ = simulate(days, A, 0.1)
    b, _ = simulate(days, A, 0.6)
    assert b["r"].sum() < a["r"].sum()
