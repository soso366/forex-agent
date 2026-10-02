"""Test de non-look-ahead (exigé par le CRITIC) : perturber le futur ne doit rien changer au présent.

1. Perturbation de toutes les minutes ≥ début du jour J : ref (médiane 20 j) du jour J inchangée, et toutes les
   colonnes (s, ATR, Δ, ref) aux minutes < J inchangées.
2. Perturbation strictement après une minute t0 (10:07 UTC du jour J) : s, ATR, Δ, ref à t0 inchangés.
   Contrôle de sensibilité : l'ATR « naïf » (étiquette M5 de début, ffill) À t0 CHANGE, ce qui montre que le test
   détecte bien la fuite signalée par le Critic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from e002 import PAIRS, PairFeatures, atr, bars

COLS = ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")


def _perturb(df: pd.DataFrame, t0: pd.Timestamp, strict_after: bool, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = df.copy()
    m = (df.index > t0) if strict_after else (df.index >= t0)
    noise = rng.normal(0, 0.003, m.sum())
    for c in COLS:
        df.loc[m, c] = df.loc[m, c].to_numpy() * (1 + noise)
    df.loc[m, "ac"] += rng.uniform(0, 0.0005, m.sum()) * df.loc[m, "ac"]
    df.loc[m, "ah"] = np.maximum(df.loc[m, "ah"], df.loc[m, "ac"])
    df["mid"] = (df["bc"] + df["ac"]) / 2
    df["spread"] = df["ac"] - df["bc"]
    return df


def _eq(a, b):
    return bool(np.array_equal(a, b, equal_nan=True))


def _naive_atr(df, t0):
    a = atr(bars(df, "5min"), 14)
    return a.reindex([t0], method="ffill").iloc[0]


def run(raw: dict) -> dict:
    res = {}
    ok = True
    for s in PAIRS:
        df = raw[s]
        base = PairFeatures(df)
        days = sorted({d for d, e in zip(base.day, base.ex) if e and d.weekday() < 5})
        J = pd.Timestamp(days[35], tz="UTC")
        pert = PairFeatures(_perturb(df, J, strict_after=False))
        k = int(base.grid.searchsorted(J))
        r = {"day": str(J.date())}
        r["ref_day_J_unchanged"] = _eq(base.ref[k:k + 1440], pert.ref[k:k + 1440])
        r["s_before_J_unchanged"] = _eq(base.s[:k], pert.s[:k])
        r["atr_before_J_unchanged"] = _eq(base.atr[:k], pert.atr[:k])
        r["delta_before_J_unchanged"] = _eq(base.delta("mid")[:k], pert.delta("mid")[:k])
        r["sanity_future_ref_changed"] = not _eq(base.ref[k + 5 * 1440:], pert.ref[k + 5 * 1440:])
        t0 = J + pd.Timedelta(hours=10, minutes=7)
        p0 = int(base.grid.searchsorted(t0))
        p2 = PairFeatures(_perturb(df, t0, strict_after=True))
        r["t0"] = str(t0)
        r["atr_t0_unchanged"] = _eq(base.atr[p0], p2.atr[p0])
        r["s_t0_unchanged"] = _eq(base.s[p0], p2.s[p0])
        r["delta_t0_unchanged"] = _eq(base.delta("mid")[p0], p2.delta("mid")[p0])
        r["ref_t0_unchanged"] = _eq(base.ref[p0], p2.ref[p0])
        r["sensitivity_naive_atr_t0_changes"] = not _eq(_naive_atr(df, t0), _naive_atr(_perturb(df, t0, True), t0))
        r["pass"] = all(v for kk, v in r.items() if kk.endswith("unchanged")) and r["sanity_future_ref_changed"] \
            and r["sensitivity_naive_atr_t0_changes"]
        ok &= r["pass"]
        res[s] = r
    res["pass"] = bool(ok)
    return res
