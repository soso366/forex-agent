"""Moteur de recherche V4 : contexte par paire, signaux des hypothèses, simulation, statistiques."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .data import PAIRS, atr, bars, load
from .sim import Market, simulate

UTC = "UTC"
PERIODS = {
    "T1": ("2025-09-08", "2025-12-01"), "T2": ("2025-12-01", "2026-03-01"),
    "V1": ("2026-03-01", "2026-06-01"), "V2": ("2026-06-01", "2026-09-01"),
}
TRAIN, VAL = ("T1", "T2"), ("V1", "V2")


def session_of(h: np.ndarray) -> np.ndarray:
    return np.select([h < 7, h < 12, h < 16, h < 21], ["asie", "londres", "overlap", "new_york"], "fin")


@dataclass
class Ctx:
    sym: str
    m1: pd.DataFrame
    m5: pd.DataFrame
    market: Market
    extra: dict = field(default_factory=dict)


def build_ctx(sym: str, locked: bool = False) -> Ctx:
    m1 = load(sym, locked)
    m5 = bars(m1, "5min")
    m5["atr"] = atr(m5).shift(1)                      # ATR connu AVANT la bougie
    m5["atr_now"] = atr(m5)
    m5["vol_ratio"] = m5["atr_now"] / m5["atr_now"].rolling(288 * 20, min_periods=288 * 5).median()
    m15 = bars(m1, "15min")
    net = (m15["c"] - m15["c"].shift(20)).abs()
    path = m15["c"].diff().abs().rolling(20).sum()
    m15["er"] = net / path
    h1 = bars(m1, "1h")
    h1["slope"] = np.sign(h1["c"].ewm(span=50, adjust=False).mean().diff(3))
    # étiquettes connues à la clôture de chaque M5 (aucune donnée future)
    t_close = m5.index + pd.Timedelta(minutes=5)
    er = m15["er"].set_axis(m15.index + pd.Timedelta(minutes=15))
    m5["er"] = er.reindex(t_close, method="ffill").to_numpy()
    sl = h1["slope"].set_axis(h1.index + pd.Timedelta(hours=1))
    m5["h1_slope"] = sl.reindex(t_close, method="ffill").to_numpy()
    m5["regime"] = np.select([(m5["er"] >= 0.3) & (m5["h1_slope"] > 0), (m5["er"] >= 0.3) & (m5["h1_slope"] < 0),
                              m5["er"] < 0.25], ["TREND_UP", "TREND_DOWN", "RANGE"], "CHOP")
    m5["vol"] = pd.cut(m5["vol_ratio"], [0, 0.8, 1.25, 99], labels=["basse", "normale", "haute"]).astype(str)
    m5["session"] = session_of(m5.index.hour)
    return Ctx(sym, m1, m5, Market(m1))


def signals_frame(ctx: Ctx, idx, direction, stop_dist, target_dist, entry_times=None) -> pd.DataFrame:
    """idx : positions des bougies M5 de signal (entrée à la clôture). Joint le contexte de la bougie."""
    idx = np.asarray(idx, dtype=int)
    b = ctx.m5.iloc[idx]
    et = (b.index + pd.Timedelta(minutes=5)) if entry_times is None else pd.DatetimeIndex(entry_times)
    return pd.DataFrame({"time": et, "sym": ctx.sym, "dir": np.asarray(direction, dtype=int),
                         "stop": np.asarray(stop_dist, float), "target": np.asarray(target_dist, float),
                         "regime": b["regime"].to_numpy(), "session": b["session"].to_numpy(),
                         "vol": b["vol"].to_numpy(), "atr": b["atr_now"].to_numpy()})


def non_overlap(sig: pd.DataFrame, hold: int = 30) -> pd.DataFrame:
    """Une position à la fois par paire : ignore un signal tant que le précédent retenu est ouvert."""
    keep, last = [], {}
    gap = pd.Timedelta(minutes=hold)
    for i, (t, s) in enumerate(zip(sig["time"], sig["sym"])):
        if s in last and t < last[s] + gap:
            continue
        keep.append(i)
        last[s] = t
    return sig.iloc[keep]


def run(ctxs: dict, sig: pd.DataFrame, hold: int = 30) -> pd.DataFrame:
    sig = non_overlap(sig.sort_values("time").reset_index(drop=True), hold)
    parts = []
    for sym, g in sig.groupby("sym"):
        res = simulate(ctxs[sym].market, g["time"], g["dir"], g["stop"], g["target"], hold)
        parts.append(pd.concat([g.reset_index(drop=True), res], axis=1))
    if not parts:
        return pd.DataFrame(columns=list(sig.columns) + ["r", "exit"])
    t = pd.concat(parts, ignore_index=True).dropna(subset=["r"]).sort_values("time")
    t["period"] = label_period(t["time"])
    return t.reset_index(drop=True)


def label_period(times) -> np.ndarray:
    times = pd.DatetimeIndex(times)
    out = np.array(["hors"] * len(times), dtype=object)
    for k, (a, b) in PERIODS.items():
        m = (times >= pd.Timestamp(a, tz=UTC)) & (times < pd.Timestamp(b, tz=UTC))
        out[m] = k
    return out


def stats(r: pd.Series) -> dict:
    r = pd.Series(r, dtype=float).dropna()
    n = len(r)
    if n == 0:
        return {"n": 0, "exp": np.nan, "t": np.nan, "pf": np.nan, "win": np.nan, "R": 0.0, "dd": 0.0, "ex_top5": np.nan}
    w, l = r[r > 0].sum(), -r[r <= 0].sum()
    sd = r.std(ddof=1) if n > 1 else np.nan
    c = r.cumsum().to_numpy()
    dd = float((np.maximum.accumulate(np.concatenate([[0], c]))[1:] - c).max())
    top = r.sort_values(ascending=False).iloc[5:]
    return {"n": n, "exp": float(r.mean()), "t": float(r.mean() / (sd / np.sqrt(n))) if sd and sd > 0 else np.nan,
            "pf": float(w / l) if l > 0 else np.inf, "win": float((r > 0).mean()), "R": float(r.sum()), "dd": dd,
            "ex_top5": float(top.mean()) if len(top) else np.nan}


def by(t: pd.DataFrame, col) -> dict:
    return {str(k): stats(g["r"]) for k, g in t.groupby(col, observed=True)}
