"""Les 5 hypothèses V4 et leurs grilles, exactement comme dans PROTOCOLE.md.

Chaque générateur reçoit le contexte d'une paire et renvoie un DataFrame de signaux (signals_frame).
Variante = dictionnaire de paramètres ; « neighbors » = variantes à un seul paramètre d'écart.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .engine import Ctx, signals_frame

INF = np.inf


def _local(idx: pd.DatetimeIndex, tz: str) -> pd.DatetimeIndex:
    return idx.tz_convert(tz)


# ---------------------------------------------------------------- H1 sweep & reclaim
def h1_sweep(ctx: Ctx, level: str, exit_: str, pen: float) -> pd.DataFrame:
    b = ctx.m5
    h = b.index.hour
    day = b.index.normalize()
    # Asie : 00:00–06:00 UTC ; PDH/PDL : jour Forex (clôture 17:00 New York)
    ny = _local(b.index, "America/New_York")
    fx_day = (ny + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    window = ((h >= 7) & (h < 10)) | ((h >= 12) & (h < 15))
    rows = []
    if level == "asie":
        asia = b[(h < 6)].groupby(day[h < 6]).agg(hi=("h", "max"), lo=("l", "min"))
        lv_hi = pd.Series(day, index=b.index).map(asia["hi"])
        lv_lo = pd.Series(day, index=b.index).map(asia["lo"])
        key = day
    else:
        d = b.groupby(fx_day).agg(hi=("h", "max"), lo=("l", "min"))
        prev = d.shift(1)
        lv_hi = pd.Series(fx_day, index=b.index).map(prev["hi"])
        lv_lo = pd.Series(fx_day, index=b.index).map(prev["lo"])
        key = fx_day
    hi, lo, c, a = b["h"].to_numpy(), b["l"].to_numpy(), b["c"].to_numpy(), b["atr"].to_numpy()
    LH, LL = lv_hi.to_numpy(), lv_lo.to_numpy()
    used = set()
    for i in np.nonzero(window)[0]:
        if not np.isfinite(a[i]) or not np.isfinite(LH[i]):
            continue
        k = key[i]
        # sweep du haut → vente
        if (k, "hi") not in used and hi[i] > LH[i] + pen * a[i] and c[i] < LH[i]:
            used.add((k, "hi"))
            sd = hi[i] + 0.1 * a[i] - c[i]
            rows.append((i, -1, sd, sd if exit_ == "1R" else INF))
        elif (k, "lo") not in used and lo[i] < LL[i] - pen * a[i] and c[i] > LL[i]:
            used.add((k, "lo"))
            sd = c[i] - (lo[i] - 0.1 * a[i])
            rows.append((i, 1, sd, sd if exit_ == "1R" else INF))
        # un niveau déjà dépassé sans retour est « consommé » aussi
        if hi[i] > LH[i] and c[i] >= LH[i]:
            used.add((k, "hi"))
        if lo[i] < LL[i] and c[i] <= LL[i]:
            used.add((k, "lo"))
    if not rows:
        return signals_frame(ctx, [], [], [], [])
    i, d, sd, td = map(np.array, zip(*rows))
    return signals_frame(ctx, i, d, sd, td)


# ---------------------------------------------------------------- H2 opening range
def h2_orb(ctx: Ctx, sess: str, stop: str, exit_: str) -> pd.DataFrame:
    b = ctx.m5
    tz, (oh, om) = ("Europe/London", (8, 0)) if sess == "londres" else ("America/New_York", (9, 30))
    loc = _local(b.index, tz)
    mins = loc.hour * 60 + loc.minute
    start = oh * 60 + om
    day = loc.normalize()
    in_or = (mins >= start) & (mins < start + 30)
    after = (mins >= start + 30) & (mins < start + 90)
    orr = b[in_or].groupby(day[in_or]).agg(hi=("h", "max"), lo=("l", "min"), n=("c", "size"))
    orr = orr[orr["n"] >= 5]
    rows, done = [], set()
    c, a = b["c"].to_numpy(), b["atr"].to_numpy()
    for i in np.nonzero(after)[0]:
        d0 = day[i]
        if d0 in done or d0 not in orr.index or not np.isfinite(a[i]):
            continue
        hi, lo = orr.at[d0, "hi"], orr.at[d0, "lo"]
        mid = (hi + lo) / 2
        if c[i] > hi:
            sd = (c[i] - mid) if stop == "milieu" else a[i]
            rows.append((i, 1, sd, 1.5 * sd if exit_ == "1.5R" else INF)); done.add(d0)
        elif c[i] < lo:
            sd = (mid - c[i]) if stop == "milieu" else a[i]
            rows.append((i, -1, sd, 1.5 * sd if exit_ == "1.5R" else INF)); done.add(d0)
    if not rows:
        return signals_frame(ctx, [], [], [], [])
    i, d, sd, td = map(np.array, zip(*rows))
    return signals_frame(ctx, i, d, sd, td)


# ---------------------------------------------------------------- H3 fix de Londres
def _last_business_day(idx: pd.DatetimeIndex) -> np.ndarray:
    d = idx.normalize().tz_localize(None)
    month_end = d + pd.offsets.BMonthEnd(0)
    return (d == month_end)


def h3_fix(ctx: Ctx, mode: str, k: float, days: str) -> pd.DataFrame:
    b = ctx.m5
    loc = _local(b.index, "Europe/London")
    mins = loc.hour * 60 + loc.minute
    c, a = b["c"].to_numpy(), b["atr"].to_numpy()
    if mode == "fade":                     # bougie 15:55–16:00 Londres : clôture = prix du fix ; entrée 16:00 (+1 min)
        sig_bar = np.nonzero(mins == 15 * 60 + 55)[0]
        lookback = 6                       # 30 min
    else:                                  # « avant fix » : à 15:30, suivre le mouvement 15:00→15:30 jusqu'à 16:00
        sig_bar = np.nonzero(mins == 15 * 60 + 25)[0]
        lookback = 6
    me = _last_business_day(b.index)
    rows = []
    for i in sig_bar:
        if i < lookback or not np.isfinite(a[i]):
            continue
        if days == "fin_mois" and not me[i]:
            continue
        move = c[i] - b["o"].iat[i - lookback + 1]
        if abs(move) < k * a[i]:
            continue
        d = -np.sign(move) if mode == "fade" else np.sign(move)
        rows.append((i, int(d), 1.5 * a[i], INF))
    if not rows:
        return signals_frame(ctx, [], [], [], [])
    i, d, sd, td = map(np.array, zip(*rows))
    times = b.index[i] + pd.Timedelta(minutes=5) + (pd.Timedelta(minutes=1) if mode == "fade" else pd.Timedelta(0))
    return signals_frame(ctx, i, d, sd, td, entry_times=times)


# ---------------------------------------------------------------- H4 fix de Tokyo (USDJPY)
def _gotobi(idx: pd.DatetimeIndex) -> np.ndarray:
    """Jours 5,10,15,20,25,30 et dernier jour ouvré ; si week-end → jour ouvré précédent."""
    days = pd.DatetimeIndex(sorted(set(idx.tz_convert("Asia/Tokyo").normalize().tz_localize(None))))
    target = set()
    months = sorted({(d.year, d.month) for d in days})
    for y, m in months:
        for dd in (5, 10, 15, 20, 25, 30):
            try:
                t = pd.Timestamp(y, m, dd)
            except ValueError:
                continue
            while t.weekday() >= 5:
                t -= pd.Timedelta(days=1)
            target.add(t)
        target.add(pd.Timestamp(y, m, 1) + pd.offsets.BMonthEnd(0))
    loc = idx.tz_convert("Asia/Tokyo").normalize().tz_localize(None)
    return np.isin(loc, pd.DatetimeIndex(sorted(target)))


def h4_tokyo(ctx: Ctx, side: str, days: str, stop_atr: float) -> pd.DataFrame:
    if ctx.sym != "USDJPY":
        return signals_frame(ctx, [], [], [], [])
    b = ctx.m5
    m = b.index.hour * 60 + b.index.minute
    # bougie dont la CLÔTURE est l'heure d'entrée : 00:20 → entrée 00:25 ; 00:50 → entrée 00:55 (+1 min = 00:56)
    sig_bar = np.nonzero(m == (20 if side == "achat_avant" else 50))[0]
    g = _gotobi(b.index)
    a = b["atr"].to_numpy()
    rows = []
    for i in sig_bar:
        if not np.isfinite(a[i]) or (days == "gotobi" and not g[i]) or b.index[i].weekday() >= 5:
            continue
        rows.append((i, 1 if side == "achat_avant" else -1, stop_atr * a[i], INF))
    if not rows:
        return signals_frame(ctx, [], [], [], [])
    i, d, sd, td = map(np.array, zip(*rows))
    times = b.index[i] + pd.Timedelta(minutes=5) + (pd.Timedelta(minutes=1) if side == "vente_apres" else pd.Timedelta(0))
    return signals_frame(ctx, i, d, sd, td, entry_times=times)


# ---------------------------------------------------------------- H5 displacement M5
def h5_disp(ctx: Ctx, mode: str, k: float, sess: str) -> pd.DataFrame:
    b = ctx.m5
    h = b.index.hour
    hours = {"toutes": (h >= 7) & (h < 17), "londres": (h >= 7) & (h < 12), "new_york": (h >= 12) & (h < 17)}[sess]
    o, hi, lo, c, a = (b[x].to_numpy() for x in ("o", "h", "l", "c", "atr"))
    body = c - o
    rng = np.maximum(hi - lo, 1e-12)
    up = (body >= k * a) & ((c - lo) / rng >= 0.75)
    dn = (-body >= k * a) & ((hi - c) / rng >= 0.75)
    ok = hours & np.isfinite(a)
    i_up, i_dn = np.nonzero(up & ok)[0], np.nonzero(dn & ok)[0]
    i = np.concatenate([i_up, i_dn])
    d = np.concatenate([np.ones(len(i_up)), -np.ones(len(i_dn))]).astype(int)
    if mode == "retour":
        d = -d
    order = np.argsort(i)
    i, d = i[order], d[order]
    return signals_frame(ctx, i, d, a[i], np.full(len(i), INF))


# ---------------------------------------------------------------- grilles
def grid():
    G = {}
    G["H1"] = (h1_sweep, [dict(level=l, exit_=e, pen=p) for l, e, p in
                          itertools.product(["asie", "pdh_pdl"], ["temps", "1R"], [0.0, 0.2])])
    G["H2"] = (h2_orb, [dict(sess=s, stop=st, exit_=e) for s, st, e in
                        itertools.product(["londres", "new_york"], ["milieu", "1ATR"], ["temps", "1.5R"])])
    G["H3"] = (h3_fix, [dict(mode="fade", k=k, days=d) for k, d in itertools.product([0.5, 1.0, 1.5], ["tous", "fin_mois"])]
               + [dict(mode="avant", k=k, days="tous") for k in (0.5, 1.0)])
    G["H4"] = (h4_tokyo, [dict(side=s, days=d, stop_atr=sa) for s, d, sa in
                          itertools.product(["achat_avant", "vente_apres"], ["tous", "gotobi"], [1.0, 2.0])])
    G["H5"] = (h5_disp, [dict(mode=m, k=k, sess="toutes") for m, k in itertools.product(["continuation", "retour"], [1.0, 1.5, 2.0])]
               + [dict(mode="continuation", k=1.5, sess=s) for s in ("londres", "new_york")])
    return G


def neighbors(variants: list[dict], v: dict) -> list[dict]:
    return [w for w in variants if sum(w[k] != v[k] for k in v) == 1]


def vname(v: dict) -> str:
    return " · ".join(f"{k.rstrip('_')}={x}" for k, x in v.items())
