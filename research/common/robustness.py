"""Tests de robustesse génériques (Quant + Critic) — extraits de la méthode appliquée à H3, sans toucher à H3.

Entrée : DataFrame de trades avec colonnes `time` (UTC, tz-aware), `sym`, `r` (R net de spread), `stop` (distance de stop
en prix). Tout est en R. Aucune fonction ne choisit de paramètre : elles mesurent.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}
COSTS = (0.0, 0.2, 0.4, 0.6, 1.0)


def stats(r) -> dict:
    r = pd.Series(r, dtype=float).dropna()
    n = len(r)
    if n == 0:
        return {"n": 0, "exp": np.nan, "t": np.nan, "pf": np.nan, "win": np.nan, "R": 0.0, "dd": 0.0}
    w, l = r[r > 0].sum(), -r[r <= 0].sum()
    sd = r.std(ddof=1) if n > 1 else np.nan
    c = r.cumsum().to_numpy()
    dd = float((np.maximum.accumulate(np.concatenate([[0], c]))[1:] - c).max())
    return {"n": n, "exp": float(r.mean()), "t": float(r.mean() / (sd / np.sqrt(n))) if sd and sd > 0 else np.nan,
            "pf": float(w / l) if l > 0 else np.inf, "win": float((r > 0).mean()), "R": float(r.sum()), "dd": dd}


def day_view(t: pd.DataFrame, tz: str = "UTC", n_boot: int = 10000, seed: int = 11) -> dict:
    """Paires corrélées (USD commun) : on agrège par jour avant de juger. IC 95 % bootstrap de l'espérance quotidienne."""
    day = pd.DatetimeIndex(t["time"]).tz_convert(tz).normalize()
    d = t.groupby(day)["r"].sum()
    rng = np.random.default_rng(seed)
    b = np.array([rng.choice(d.to_numpy(), len(d)).mean() for _ in range(n_boot)]) if len(d) else np.array([np.nan])
    return {"days": int(len(d)), "win_days": int((d > 0).sum()), "lose_days": int((d < 0).sum()),
            "mean_R_per_day": float(d.mean()) if len(d) else np.nan,
            "ci95": [float(np.quantile(b, .025)), float(np.quantile(b, .975))]}


def one_per_day(t: pd.DataFrame, priority=("EURUSD", "GBPUSD", "USDJPY"), tz: str = "UTC") -> dict:
    x = t.assign(_d=pd.DatetimeIndex(t["time"]).tz_convert(tz).normalize(),
                 _p=t["sym"].map({s: i for i, s in enumerate(priority)}))
    return stats(x.sort_values(["_d", "_p"]).groupby("_d").head(1)["r"])


def costs(t: pd.DataFrame, extra_pips=COSTS) -> dict:
    """Coût TOTAL supplémentaire par trade (aller-retour), en pips."""
    return {str(x): stats(t["r"] - x * t["sym"].map(PIP) / t["stop"]) for x in extra_pips}


def quarters(t: pd.DataFrame) -> dict:
    """Blocs de 3 mois fixes : sept.–nov., déc.–fév., mars–mai, juin–août."""
    m = pd.DatetimeIndex(t["time"]).tz_convert("UTC").month
    q = np.select([np.isin(m, [9, 10, 11]), np.isin(m, [12, 1, 2]), np.isin(m, [3, 4, 5])],
                  ["Q1 sept-nov", "Q2 déc-fév", "Q3 mars-mai"], "Q4 juin-août")
    return {k: stats(g["r"]) for k, g in t.assign(_q=q).groupby("_q")}


def concentration(t: pd.DataFrame, tz: str = "UTC") -> dict:
    day = pd.DatetimeIndex(t["time"]).tz_convert(tz).normalize().tz_localize(None)
    x = t.assign(_d=day, _me=(day == day + pd.offsets.BMonthEnd(0)))
    dsum = x.groupby("_d")["r"].sum()
    top5 = set(dsum.sort_values(ascending=False).index[:5])
    tot = x["r"].sum()
    q = quarters(t)
    best_q = max(q, key=lambda k: q[k]["R"]) if q else None
    m = pd.DatetimeIndex(t["time"]).tz_convert("UTC").month
    qlab = np.select([np.isin(m, [9, 10, 11]), np.isin(m, [12, 1, 2]), np.isin(m, [3, 4, 5])],
                     ["Q1 sept-nov", "Q2 déc-fév", "Q3 mars-mai"], "Q4 juin-août")
    pairs = {s: g["r"].sum() for s, g in x.groupby("sym")}
    best_p = max(pairs, key=pairs.get) if pairs else None
    return {
        "top5_days_share": float(dsum[list(top5)].sum() / tot) if tot else None,
        "month_end_share": float(x.loc[x["_me"], "r"].sum() / tot) if tot else None,
        "without_top5_days": stats(x.loc[~x["_d"].isin(top5), "r"]),
        "without_month_end": stats(x.loc[~x["_me"], "r"]),
        "without_best_quarter": {"quarter": best_q, **stats(x.loc[qlab != best_q, "r"])},
        "without_best_pair": {"pair": best_p, **stats(x.loc[x["sym"] != best_p, "r"])},
    }


def placebo(make_trades: Callable[[object], pd.DataFrame], alternatives: list) -> dict:
    """Même règle appliquée à des conditions alternatives PRÉDÉFINIES (heures, jours…). Renvoie les stats de chacune."""
    return {str(a): stats(make_trades(a)["r"]) for a in alternatives}


def full_report(t: pd.DataFrame, tz: str = "UTC") -> dict:
    return {"global": stats(t["r"]), "pairs": {s: stats(g["r"]) for s, g in t.groupby("sym")},
            "quarters": quarters(t), "costs": costs(t), "day_view": day_view(t, tz),
            "one_per_day": one_per_day(t, tz=tz), "concentration": concentration(t, tz)}
