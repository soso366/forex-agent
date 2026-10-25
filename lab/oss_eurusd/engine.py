"""Moteur de backtest isolé pour les tests de projets GitHub EUR/USD.

Aucun lien avec le robot principal (forex_agent/). Simulation uniquement.
Conventions (voir PROTOCOLE.md) :
  - données M1 BID/ASK réelles, bougies H1/M5 reconstruites en UTC ;
  - indicateurs calculés comme MetaTrader 5, sur le BID ;
  - achat au ASK, vente au BID, stop/objectif suivis minute par minute,
    stop d'abord si les deux sont touchés dans la même minute.
"""
from __future__ import annotations

import gzip
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PIP = 0.0001
POINT = 0.00001
CONTRACT = 100_000          # 1 lot EUR/USD
TICK_VALUE = 1.0            # $ par point et par lot (compte USD)
LOT_STEP = 0.01
LOT_MIN = 0.01
LOT_MAX = 100.0


# --------------------------------------------------------------------------- données
def load_m1(paths: list[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        with gzip.open(p, "rt") as fh:
            frames.append(pd.read_csv(fh))
    df = pd.concat(frames, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    bad = (df["ask_close"] < df["bid_close"]) | (df["bid_high"] < df["bid_low"])
    if bad.any():
        raise ValueError(f"{int(bad.sum())} minutes incohérentes")
    return df


def resample(m1: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Bougies BID/ASK + index de la première minute de chaque bougie."""
    key = m1["time"].dt.floor(rule)
    g = m1.assign(_i=np.arange(len(m1))).groupby(key, sort=True)
    bars = pd.DataFrame({
        "bid_open": g["bid_open"].first(), "bid_high": g["bid_high"].max(),
        "bid_low": g["bid_low"].min(), "bid_close": g["bid_close"].last(),
        "start": g["_i"].first(),
    })
    bars.index.name = "time"
    return bars.reset_index()


# --------------------------------------------------------------------------- indicateurs MT5
def rsi_mt5(close: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(close), np.nan)
    if len(close) <= n:
        return out
    d = np.diff(close)
    gain = np.clip(d, 0, None)
    loss = np.clip(-d, 0, None)
    ag, al = gain[:n].mean(), loss[:n].mean()

    def val(ag, al):
        if al != 0.0:
            return 100.0 - 100.0 / (1.0 + ag / al)
        return 100.0 if ag != 0.0 else 50.0

    out[n] = val(ag, al)
    for i in range(n + 1, len(close)):
        ag = (ag * (n - 1) + gain[i - 1]) / n
        al = (al * (n - 1) + loss[i - 1]) / n
        out[i] = val(ag, al)
    return out


def bands_mt5(close: np.ndarray, n: int, dev: float):
    s = pd.Series(close)
    mid = s.rolling(n).mean()
    std = s.rolling(n).std(ddof=0)          # écart-type de population (MT5 StdDev_Func)
    return (mid + dev * std).to_numpy(), mid.to_numpy(), (mid - dev * std).to_numpy()


def atr_mt5(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    prev = np.concatenate([[np.nan], close[:-1]])
    tr = np.where(np.isnan(prev), high - low,
                  np.maximum(high, prev) - np.minimum(low, prev))
    atr = pd.Series(tr).rolling(n).mean().to_numpy().copy()   # moyenne simple, comme ATR.mq5
    atr[:n] = np.nan
    return atr


def server_hour(times: pd.Series, mode: str) -> np.ndarray:
    if mode == "utc":
        return times.dt.hour.to_numpy()
    if mode == "eet_ny":   # serveur « clôture New York à minuit » : UTC+2 / UTC+3 en été US
        return (times.dt.tz_convert("America/New_York") + pd.Timedelta(hours=7)).dt.hour.to_numpy()
    raise ValueError(mode)


def normalize_lot_floor(lot: float) -> float:
    """smizxe : arrondi vers le bas, refus si < minimum."""
    lot = math.floor(lot / LOT_STEP + 1e-9) * LOT_STEP
    if lot < LOT_MIN:
        return 0.0
    return round(min(lot, LOT_MAX), 2)


def normalize_lot_clamp(lot: float) -> float:
    """sbrakni : borné au minimum (prend alors plus de risque), puis arrondi."""
    lot = min(max(lot, LOT_MIN), LOT_MAX)
    return round(round(lot / LOT_STEP) * LOT_STEP, 2)


# --------------------------------------------------------------------------- simulateur
@dataclass
class Costs:
    name: str
    commission_per_lot: float      # $ aller-retour
    slippage_pips: float           # défavorable, sur chaque ordre au marché


@dataclass
class Position:
    side: int          # +1 achat, -1 vente
    entry: float
    sl: float
    tp: float
    lots: float
    i_entry: int
    t_entry: pd.Timestamp
    next_i: int
    tag: str = ""


@dataclass
class Sim:
    m1: pd.DataFrame
    costs: Costs
    balance: float
    i_end: int                                   # première minute hors période
    pos: Position | None = None
    trades: list = field(default_factory=list)
    equity: list = field(default_factory=list)
    ambiguous: int = 0
    refused_lot: int = 0

    def __post_init__(self):
        m = self.m1
        self.t = m["time"]
        self.bo, self.bh, self.bl, self.bc = (m[c].to_numpy() for c in ("bid_open", "bid_high", "bid_low", "bid_close"))
        self.ao, self.ah, self.al, self.ac = (m[c].to_numpy() for c in ("ask_open", "ask_high", "ask_low", "ask_close"))
        self.start_balance = self.balance

    @property
    def slip(self) -> float:
        return self.costs.slippage_pips * PIP

    def open(self, side: int, i: int, quote: float, sl: float, tp: float, lots: float, tag: str = ""):
        fill = quote + self.slip if side > 0 else quote - self.slip
        self.pos = Position(side, fill, sl, tp, lots, i, self.t.iloc[i], i, tag)

    def _close(self, i: int, price: float, reason: str):
        p = self.pos
        gross = (price - p.entry) * p.side * CONTRACT * p.lots
        comm = self.costs.commission_per_lot * p.lots
        pnl = gross - comm
        self.balance += pnl
        risk = abs(p.entry - p.sl) * CONTRACT * p.lots
        self.trades.append({
            "t_entry": p.t_entry, "t_exit": self.t.iloc[min(i, len(self.t) - 1)], "side": p.side,
            "entry": p.entry, "exit": price, "sl": p.sl, "tp": p.tp, "lots": p.lots,
            "pnl": pnl, "commission": comm, "pips": (price - p.entry) * p.side / PIP,
            "r": pnl / risk if risk > 0 else np.nan, "reason": reason, "tag": p.tag,
        })
        self.pos = None

    def advance_to(self, i_stop: int):
        """Suit stop/objectif sur les minutes [pos.next_i, i_stop)."""
        p = self.pos
        if p is None:
            return
        i_stop = min(i_stop, self.i_end)
        a, b = p.next_i, i_stop
        if b <= a:
            return
        if p.side > 0:
            o, hi, lo = self.bo[a:b], self.bh[a:b], self.bl[a:b]
            hit_sl, hit_tp = lo <= p.sl, (hi >= p.tp) if p.tp > 0 else np.zeros(b - a, bool)
            gap_sl, gap_tp = o <= p.sl, (o >= p.tp) if p.tp > 0 else np.zeros(b - a, bool)
        else:
            o, hi, lo = self.ao[a:b], self.ah[a:b], self.al[a:b]
            hit_sl, hit_tp = hi >= p.sl, (lo <= p.tp) if p.tp > 0 else np.zeros(b - a, bool)
            gap_sl, gap_tp = o >= p.sl, (o <= p.tp) if p.tp > 0 else np.zeros(b - a, bool)
        if a == p.i_entry:           # minute d'entrée : l'ouverture est le prix d'entrée lui-même
            gap_sl[0] = gap_tp[0] = False
        any_hit = hit_sl | hit_tp
        if not any_hit.any():
            p.next_i = b
            return
        k = int(np.argmax(any_hit))
        i = a + k
        if gap_sl[k]:
            self._close(i, o[k] - p.side * self.slip, "stop_gap")
        elif gap_tp[k]:
            self._close(i, o[k], "objectif_gap")
        elif hit_sl[k]:
            if hit_tp[k]:
                self.ambiguous += 1
            self._close(i, p.sl - p.side * self.slip, "stop")
        else:
            self._close(i, p.tp, "objectif")

    def close_market(self, i: int, reason: str):
        p = self.pos
        price = (self.bo[i] - self.slip) if p.side > 0 else (self.ao[i] + self.slip)
        self._close(i, price, reason)

    def close_end(self):
        if self.pos is None:
            return
        self.advance_to(self.i_end)
        if self.pos is not None:
            i = self.i_end - 1
            p = self.pos
            price = (self.bc[i] - self.slip) if p.side > 0 else (self.ac[i] + self.slip)
            self._close(i, price, "fin_de_periode")

    def mark(self, i: int):
        eq = self.balance
        if self.pos is not None:
            p = self.pos
            px = self.bo[i] if p.side > 0 else self.ao[i]
            eq += (px - p.entry) * p.side * CONTRACT * p.lots
        self.equity.append(eq)


# --------------------------------------------------------------------------- métriques
def metrics(sim: Sim) -> dict:
    tr = pd.DataFrame(sim.trades)
    eq = np.array(sim.equity + [sim.balance], dtype=float)
    peak = np.maximum.accumulate(eq)
    dd = float(np.max((peak - eq) / peak)) if len(eq) else 0.0
    out = {
        "trades": int(len(tr)), "capital_initial": sim.start_balance,
        "capital_final": round(sim.balance, 2),
        "rentabilite_pct": round((sim.balance / sim.start_balance - 1) * 100, 2),
        "drawdown_max_pct": round(dd * 100, 2),
        "stop_objectif_meme_minute": sim.ambiguous, "entrees_refusees_lot_trop_petit": sim.refused_lot,
    }
    if len(tr) == 0:
        out.update(profit_factor=None, taux_reussite_pct=None, gain_moyen_pips=None,
                   esperance_r=None, achats=0, ventes=0, t_stat=None, commissions=0.0)
        return out
    gp = tr.loc[tr.pnl > 0, "pnl"].sum()
    gl = -tr.loc[tr.pnl < 0, "pnl"].sum()
    rets = tr["pnl"].to_numpy()
    t_stat = float(rets.mean() / (rets.std(ddof=1) / math.sqrt(len(rets)))) if len(rets) > 2 and rets.std(ddof=1) > 0 else None
    out.update(
        profit_factor=round(gp / gl, 3) if gl > 0 else None,
        taux_reussite_pct=round((tr.pnl > 0).mean() * 100, 1),
        gain_moyen_pips=round(tr.pips.mean(), 2),
        esperance_r=round(tr.r.mean(), 3),
        achats=int((tr.side > 0).sum()), ventes=int((tr.side < 0).sum()),
        t_stat=round(t_stat, 2) if t_stat is not None else None,
        commissions=round(tr.commission.sum(), 2),
        sorties=tr.reason.value_counts().to_dict(),
    )
    return out
