"""Moteur de simulation pour les 10 méthodes documentées (voir PROTOCOLE.md).

Bougies H1 BID/ASK reconstruites depuis le M1 Dukascopy ; journées de trading 17 h New York → 17 h New York.
Plusieurs unités possibles (pyramide Turtle). Achat au ASK, vente au BID. Ordres stop déclenchés sur le BID
(niveau de prix) et exécutés au ASK pour un achat ; cas défavorable retenu quand l'ordre n'est pas déterminable.
"""
from __future__ import annotations

import gzip
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

CONTRACT = 100_000
PIP = 0.0001


# --------------------------------------------------------------------------- données
def load_m1(paths):
    frames = []
    for p in paths:
        with gzip.open(p, "rt") as fh:
            frames.append(pd.read_csv(fh))
    df = pd.concat(frames, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def hourly(m1):
    key = m1["time"].dt.floor("1h")
    g = m1.groupby(key, sort=True)
    h = pd.DataFrame({
        "bo": g["bid_open"].first(), "bh": g["bid_high"].max(), "bl": g["bid_low"].min(), "bc": g["bid_close"].last(),
        "ao": g["ask_open"].first(), "ah": g["ask_high"].max(), "al": g["ask_low"].min(), "ac": g["ask_close"].last(),
    })
    h["m0"] = m1.assign(_i=np.arange(len(m1))).groupby(key, sort=True)["_i"].first()
    h.index.name = "time"
    h = h.reset_index()
    h.attrs["m1_bh"] = m1["bid_high"].to_numpy()
    h.attrs["m1_bl"] = m1["bid_low"].to_numpy()
    h.attrs["m1_bo"] = m1["bid_open"].to_numpy()
    ny = h["time"].dt.tz_convert("America/New_York")
    h["day"] = pd.to_datetime((ny + pd.Timedelta(hours=7)).dt.date)          # jour de trading (17 h NY)
    h["ny_hour"] = ny.dt.hour
    h["ldn_hour"] = h["time"].dt.tz_convert("Europe/London").dt.hour
    h["weekday"] = h["day"].dt.weekday
    return h


def daily(h):
    g = h.groupby("day", sort=True)
    d = pd.DataFrame({"open": g["bo"].first(), "high": g["bh"].max(), "low": g["bl"].min(), "close": g["bc"].last()})
    d = d[d.index.weekday < 5]                     # écarte les quelques minutes du dimanche soir rattachées au lundi
    return d


def wilder_atr(d, n):
    prev = d["close"].shift(1)
    tr = np.maximum(d["high"], prev) - np.minimum(d["low"], prev)
    tr.iloc[0] = d["high"].iloc[0] - d["low"].iloc[0]
    out = np.full(len(d), np.nan)
    v = tr.to_numpy()
    if len(v) > n:
        out[n - 1] = v[:n].mean()
        for i in range(n, len(v)):
            out[i] = (out[i - 1] * (n - 1) + v[i]) / n
    return pd.Series(out, index=d.index)


def rsi(close, n):
    d = close.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    au = up.ewm(alpha=1 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + au / ad.replace(0, np.nan))


# --------------------------------------------------------------------------- simulateur
@dataclass
class Costs:
    name: str
    commission: float      # $ par lot aller-retour
    slip_pips: float


@dataclass
class Unit:
    side: int
    entry: float
    lots: float
    t: pd.Timestamp
    stop: float = np.nan


@dataclass
class Book:
    costs: Costs
    equity0: float = 10_000.0
    balance: float = 10_000.0
    units: list = field(default_factory=list)
    trades: list = field(default_factory=list)       # une ligne par épisode (toutes unités fermées ensemble)
    curve: list = field(default_factory=list)
    ambiguous: int = 0
    episode_pnl: float = 0.0
    episode_start: pd.Timestamp | None = None
    episode_units: int = 0

    @property
    def slip(self):
        return self.costs.slip_pips * PIP

    @property
    def side(self):
        return self.units[0].side if self.units else 0

    def open(self, side, price_bid, spread, lots, t, stop=np.nan):
        """Exécution : achat au ASK (= bid + spread) + glissement ; vente au BID − glissement."""
        if lots <= 0:
            return
        px = price_bid + spread + self.slip if side > 0 else price_bid - self.slip
        if not self.units:
            self.episode_pnl, self.episode_start, self.episode_units = 0.0, t, 0
        self.units.append(Unit(side, px, round(lots, 2), t, stop))
        self.episode_units += 1
        self.balance -= self.costs.commission / 2 * round(lots, 2)
        self.episode_pnl -= self.costs.commission / 2 * round(lots, 2)

    def close_all(self, price_bid, spread, t, reason):
        if not self.units:
            return
        side = self.side
        px = price_bid - self.slip if side > 0 else price_bid + spread + self.slip
        lots = 0.0
        for u in self.units:
            pnl = (px - u.entry) * u.side * CONTRACT * u.lots - self.costs.commission / 2 * u.lots
            self.balance += pnl
            self.episode_pnl += pnl
            lots += u.lots
        self.trades.append({"t_entry": self.episode_start, "t_exit": t, "side": side, "units": self.episode_units,
                            "lots": round(lots, 2), "exit": px, "pnl": self.episode_pnl, "reason": reason})
        self.units = []

    def mark(self, bid, ask):
        eq = self.balance
        for u in self.units:
            px = bid if u.side > 0 else ask
            eq += (px - u.entry) * u.side * CONTRACT * u.lots
        self.curve.append(eq)
        return eq


def lots_for_risk(equity, risk_frac, dist):
    if not (dist > 0) or equity <= 0:
        return 0.0
    return math.floor(equity * risk_frac / (dist * CONTRACT) / 0.01) * 0.01


def lots_for_notional(equity, price, mult=1.0):
    return math.floor(equity * mult / (price * CONTRACT) / 0.01) * 0.01


def minute_path(h, i, side, entry_level, stop_level):
    """Dans l'heure i : l'entrée (franchissement de entry_level) précède-t-elle le stop ? Renvoie
    (entrée_touchée, stop_après_entrée, ambigu). Résolution à la minute ; même minute = ambigu (stop retenu)."""
    a = int(h["m0"].iloc[i])
    b = int(h["m0"].iloc[i + 1]) if i + 1 < len(h) else len(h.attrs["m1_bh"])
    H, L = h.attrs["m1_bh"][a:b], h.attrs["m1_bl"][a:b]
    hit = H >= entry_level if side > 0 else L <= entry_level
    if not hit.any():
        return False, False, False
    k = int(np.argmax(hit))
    st = L[k:] <= stop_level if side > 0 else H[k:] >= stop_level
    if not st.any():
        return True, False, False
    return True, True, bool(st[0])


def stop_fill(bar, level, direction):
    """Prix BID d'exécution d'un ordre stop touché dans la bougie (direction +1 = franchissement vers le haut)."""
    if direction > 0:
        return bar.bo if bar.bo >= level else level
    return bar.bo if bar.bo <= level else level


# --------------------------------------------------------------------------- métriques
def summarize(book, start, end):
    tr = pd.DataFrame(book.trades)
    eq = np.array([book.equity0] + book.curve + [book.balance])
    peak = np.maximum.accumulate(eq)
    dd = float(np.max((peak - eq) / peak)) * 100
    out = {"trades": int(len(tr)), "rentabilite_pct": round((book.balance / book.equity0 - 1) * 100, 2),
           "drawdown_max_pct": round(dd, 2), "ambigus": book.ambiguous}
    if len(tr):
        p = tr["pnl"].to_numpy()
        gp, gl = p[p > 0].sum(), -p[p < 0].sum()
        out["pf"] = round(gp / gl, 3) if gl > 0 else None
        out["reussite_pct"] = round(100 * (p > 0).mean(), 1)
        out["t_stat"] = round(float(p.mean() / (p.std(ddof=1) / math.sqrt(len(p)))), 2) if len(p) > 2 and p.std(ddof=1) > 0 else None
        streak = best = 0
        for x in p:
            streak = streak + 1 if x < 0 else 0
            best = max(best, streak)
        out["pertes_consecutives_max"] = int(best)
    else:
        out.update(pf=None, reussite_pct=None, t_stat=None, pertes_consecutives_max=0)
    return out
