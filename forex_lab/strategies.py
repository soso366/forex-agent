"""Règles des candidates du lot 1, traduites ligne à ligne depuis leur source (voir candidates.yaml)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import (Rules, bands, cci, change_in_pct, ema, macd, pip, rsi, sma, stochastic, wpr)

PROJET = dict(cap_min=240, flat_utc_hour=21, entry_hours_utc=(0, 20), weekdays_only=True)


def f01_macd_sample(b: pd.DataFrame, sym: str):
    main, sig = macd(b["close"], 12, 26, 9)
    e = ema(b["close"], 26)
    m1, s1 = main.shift(1), sig.shift(1)
    lo, lc = 3 * pip(sym), 2 * pip(sym)
    long_ = (main < 0) & (main > sig) & (m1 < s1) & (main.abs() > lo) & (e > e.shift(1))
    short = (main > 0) & (main < sig) & (m1 > s1) & (main > lo) & (e < e.shift(1))
    ex_long = (main > 0) & (main < sig) & (m1 > s1) & (main > lc)
    ex_short = (main < 0) & (main > sig) & (m1 < s1) & (main.abs() > lc)
    return long_, short, ex_long, ex_short


def f02_moving_average(b: pd.DataFrame, sym: str):
    # MA(12) décalée de 6 : à l'ouverture de la bougie i+1, la valeur affichée est la SMA terminée à i-5
    ma = sma(b["close"], 12).shift(5)
    long_ = (b["open"] < ma) & (b["close"] > ma)
    short = (b["open"] > ma) & (b["close"] < ma)
    return long_, short, short, long_


def f04_ea_rsi(b, sym):
    r = rsi((b["high"] + b["low"] + 2 * b["close"]) / 4, 16)
    lvl = 24.0
    long_ = (r < 50 - lvl) & (r > r.shift(1)) & (change_in_pct(r.shift(2), r) > lvl / 10)
    short = (r > 50 + lvl) & (r < r.shift(1)) & (change_in_pct(r.shift(2), r) < lvl / 10)
    return long_, short, None, None


def f05_ea_cci(b, sym):
    c = cci(b, 20)
    lvl = 90.0
    long_ = (c < -lvl) & (c > c.shift(1)) & (c.shift(1) > c.shift(2))
    short = (c > lvl) & (c < c.shift(1)) & (c.shift(1) < c.shift(2))
    return long_, short, None, None


def f06_ea_wpr(b, sym):
    w = wpr(b, 18)
    lvl = 40.0
    long_ = (w > -50 - lvl) & (w.rolling(4).min() < -50 - lvl) & (w > w.shift(1)) & (change_in_pct(w.shift(3), w) > abs(lvl / 10))
    short = (w < -50 + lvl) & (w.rolling(4).max() > -50 + lvl) & (w < w.shift(1)) & (change_in_pct(w.shift(3), w) < abs(lvl / 10))
    return long_, short, None, None


def f07_ea_stochastic(b, sym):
    main, sig = stochastic(b, 8, 12, 12, "ema")
    lvl = 24.0
    lo = pd.concat([main, sig], axis=1).min(axis=1).rolling(4).min()
    hi = pd.concat([main, sig], axis=1).max(axis=1).rolling(4).max()
    long_ = (lo < 50 - lvl) & (sig < main) & (main > main.shift(1)) & (sig > sig.shift(1)) & \
            (change_in_pct(sig.shift(3), sig) > lvl / 10)
    short = (hi > 50 + lvl) & (sig > main) & (main < main.shift(1)) & (sig < sig.shift(1)) & \
            (change_in_pct(sig.shift(3), sig) < lvl / 10)
    return long_, short, None, None


def f08_ea_bands(b, sym):
    lower, base, upper = bands(b["open"], 24, 1.0)
    lvl = 2 * pip(sym)
    long_ = b["low"].rolling(3).min() + lvl < lower.rolling(3).max()
    short = b["high"].rolling(3).max() - lvl > upper.rolling(3).min()
    return long_, short, None, None


# id → (fonction, timeframe en minutes, règles exactes, règles projet)
BAR_STRATEGIES = {
    "F01": (f01_macd_sample, 60, Rules(tp_pips=50, trail_pips=30), Rules(tp_pips=50, trail_pips=30, **PROJET)),
    "F02": (f02_moving_average, 60, Rules(), Rules(**PROJET)),
    "F04": (f04_ea_rsi, 15, Rules(max_bars=30), Rules(max_bars=30, **PROJET)),
    "F05": (f05_ea_cci, 15, Rules(max_bars=30), Rules(max_bars=30, **PROJET)),
    "F06": (f06_ea_wpr, 15, Rules(max_bars=30), Rules(max_bars=30, **PROJET)),
    "F07": (f07_ea_stochastic, 15, Rules(max_bars=30), Rules(max_bars=30, **PROJET)),
    "F08": (f08_ea_bands, 15, Rules(max_bars=30), Rules(max_bars=30, **PROJET)),
}

# F03 : horaires New York (heure d'été gérée) — (heure d'entrée, heure de sortie, sens sur la paire)
F03_SCHEDULE = {
    "exact": [(3, 11, -1), (11, 16, +1)],
    "projet": [(7, 11, -1), (11, 15, +1)],
}


def f03_trades(sim, start: pd.Timestamp, end: pd.Timestamp, version: str):
    from .engine import Rules as R
    trades = []
    for day in pd.date_range(start.tz_convert("America/New_York").normalize(), end.tz_convert("America/New_York").normalize(), freq="D"):
        if day.weekday() >= 5:
            continue
        for h0, h1, side in F03_SCHEDULE[version]:
            t0 = (day + pd.Timedelta(hours=h0)).tz_convert("UTC")
            t1 = (day + pd.Timedelta(hours=h1)).tz_convert("UTC")
            if t0 < start or t1 > end:
                continue
            tr = sim.run_position(side, t0, R(), hard_exit=t1)
            if tr is not None and tr.entry_time < t1:
                trades.append(tr)
    return trades


def f03_events(pair: str, start: pd.Timestamp, end: pd.Timestamp, version: str):
    """Mêmes horaires que f03_trades, sous forme d'ordres candidats pour le simulateur de portefeuille."""
    from .engine import Event, Rules as R
    out = []
    for day in pd.date_range(start.tz_convert("America/New_York").normalize(), end.tz_convert("America/New_York").normalize(), freq="D"):
        if day.weekday() >= 5:
            continue
        for h0, h1, side in F03_SCHEDULE[version]:
            t0 = (day + pd.Timedelta(hours=h0)).tz_convert("UTC")
            t1 = (day + pd.Timedelta(hours=h1)).tz_convert("UTC")
            if t0 >= start and t1 <= end:
                out.append(Event(t0, pair, side, R(), None, None, t1, "F03"))
    return out
