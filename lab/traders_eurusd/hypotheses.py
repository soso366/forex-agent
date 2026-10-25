"""Hypothèses H-K, H-E, H-T (voir PROTOCOLE.md). Ce ne sont PAS les stratégies des traders."""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "oss_eurusd"))
from engine import PIP, POINT, TICK_VALUE, atr_mt5, bands_mt5, normalize_lot_floor, rsi_mt5  # noqa: E402

RISK_PCT = 1.0


def _open(sim, side, m0, sl_dist, tp_dist, tag):
    if not (sl_dist > 0 and tp_dist > 0):
        return
    lots = normalize_lot_floor(sim.balance * RISK_PCT / 100.0 / ((sl_dist / POINT) * TICK_VALUE))
    if lots <= 0:
        sim.refused_lot += 1
        return
    quote = sim.ao[m0] if side > 0 else sim.bo[m0]
    sim.open(side, m0, quote, round(quote - side * sl_dist, 5), round(quote + side * tp_dist, 5), lots, tag)


# ------------------------------------------------------------------ H-K
HK_GRID = [dict(k=k, r=r, m=m) for k, r, m in product((2.0, 2.5), (25, 30), (1, 2))]
HK_DEFAULT = dict(k=2.0, r=30, m=1)


def prep_hk(m1, bars_cache):
    return bars_cache["1h"]


def run_hk(sim, bars, i0, i1, p):
    c = bars["bid_close"].to_numpy()
    bbu, _, bbl = bands_mt5(c, 20, p["k"])
    rsi = rsi_mt5(c, 14)
    atr = atr_mt5(bars["bid_high"].to_numpy(), bars["bid_low"].to_numpy(), c, 14)
    t = bars["time"]
    start = bars["start"].to_numpy()
    for b in range(max(i0, 2), i1):
        m0 = int(start[b])
        sim.advance_to(m0)
        sim.mark(m0)
        if sim.pos is not None:
            if t.iloc[b] - sim.pos.t_entry >= pd.Timedelta(hours=48):
                sim.close_market(m0, "sortie_48h")
            continue
        if np.isnan(bbu[b - 1]) or np.isnan(rsi[b - 1]) or np.isnan(atr[b - 1]):
            continue
        a = atr[b - 1] * p["m"]
        if c[b - 1] > bbu[b - 1] and rsi[b - 1] > 100 - p["r"]:
            _open(sim, -1, m0, 1.0 * a, 0.5 * a, "HK_vente")
        elif c[b - 1] < bbl[b - 1] and rsi[b - 1] < p["r"]:
            _open(sim, 1, m0, 1.0 * a, 0.5 * a, "HK_achat")


# ------------------------------------------------------------------ H-E
HE_GRID = [dict(n=n, f=f, lo=lo, hi=100 - lo) for n, f, lo in product((20, 50), (0.5, 1.0), (40, 35))]
HE_DEFAULT = dict(n=50, f=0.5, lo=40, hi=60)


def daily_bars(m1):
    """Jours de trading clôturant à 17 h New York (DST automatique)."""
    day = (m1["time"].dt.tz_convert("America/New_York") + pd.Timedelta(hours=7)).dt.date
    g = m1.groupby(day, sort=True)
    d = pd.DataFrame({"high": g["bid_high"].max(), "low": g["bid_low"].min(), "close": g["bid_close"].last()})
    d.index = pd.to_datetime(d.index)
    return d


def prep_he(m1, bars_cache):
    return bars_cache["4h"], bars_cache["daily"]


def run_he(sim, prep, i0, i1, p):
    bars, d = prep
    ema = d["close"].ewm(span=p["n"], adjust=False).mean().to_numpy().copy()
    ema[: p["n"] - 1] = np.nan
    datr = atr_mt5(d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy(), 14)
    dclose = d["close"].to_numpy()
    dkeys = d.index.to_numpy()
    c = bars["bid_close"].to_numpy()
    rsi = rsi_mt5(c, 14)
    t = bars["time"]
    bar_day = pd.to_datetime((t.dt.tz_convert("America/New_York") + pd.Timedelta(hours=7)).dt.date).to_numpy()
    start = bars["start"].to_numpy()
    for b in range(max(i0, 2), i1):
        m0 = int(start[b])
        sim.advance_to(m0)
        sim.mark(m0)
        if sim.pos is not None:
            if t.iloc[b] - sim.pos.t_entry >= pd.Timedelta(days=5):
                sim.close_market(m0, "sortie_5j")
            continue
        j = int(np.searchsorted(dkeys, bar_day[b])) - 1      # dernier jour COMPLET
        if j < 0 or np.isnan(ema[j]) or np.isnan(datr[j]) or np.isnan(rsi[b - 1]):
            continue
        dist = p["f"] * datr[j]
        if dclose[j] > ema[j] and rsi[b - 1] < p["lo"]:
            _open(sim, 1, m0, dist, dist, "HE_achat")
        elif dclose[j] < ema[j] and rsi[b - 1] > p["hi"]:
            _open(sim, -1, m0, dist, dist, "HE_vente")


# ------------------------------------------------------------------ H-T
HT_GRID = [dict(R=R, hmax=h, cap=cap) for R, h, cap in product((1.5, 2.0), (12, 16), (30, 40))]
HT_DEFAULT = dict(R=1.5, hmax=12, cap=40)


def prep_ht(m1, bars_cache):
    bars = bars_cache["15min"]
    asia = m1[m1["time"].dt.hour < 7]
    g = asia.groupby(asia["time"].dt.date)
    rng = pd.DataFrame({"hi": g["bid_high"].max(), "lo": g["bid_low"].min()})
    return bars, rng


def run_ht(sim, prep, i0, i1, p):
    bars, rng = prep
    c = bars["bid_close"].to_numpy()
    t = bars["time"]
    hours = t.dt.hour.to_numpy()
    dates = t.dt.date.to_numpy()
    start = bars["start"].to_numpy()
    traded = set()
    for b in range(max(i0, 2), i1):
        m0 = int(start[b])
        sim.advance_to(m0)
        sim.mark(m0)
        if sim.pos is not None:
            if hours[b] >= p["hmax"] or dates[b] != sim.pos.t_entry.date():
                sim.close_market(m0, "sortie_horaire")
            continue
        d = dates[b - 1]
        if d != dates[b] or d in traded or not (7 <= hours[b - 1] < 11) or hours[b] >= p["hmax"]:
            continue
        if d not in rng.index:
            continue
        hi, lo = rng.at[d, "hi"], rng.at[d, "lo"]
        if (hi - lo) < 10 * PIP:
            continue
        cap = p["cap"] * PIP
        if c[b - 1] > hi:
            quote = sim.ao[m0]
            sl = min(quote - lo, cap)
            _open(sim, 1, m0, sl, p["R"] * sl, "HT_achat")
            traded.add(d)
        elif c[b - 1] < lo:
            quote = sim.bo[m0]
            sl = min(hi - quote, cap)
            _open(sim, -1, m0, sl, p["R"] * sl, "HT_vente")
            traded.add(d)


HYPOTHESES = {
    "H-K_retournement_court": (prep_hk, run_hk, HK_GRID, HK_DEFAULT),
    "H-E_repli_tendance_journaliere": (prep_he, run_he, HE_GRID, HE_DEFAULT),
    "H-T_cassure_Londres": (prep_ht, run_ht, HT_GRID, HT_DEFAULT),
}
