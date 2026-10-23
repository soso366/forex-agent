"""Moteur de backtest du Forex Strategy Research Lab.

Données : CSV Dukascopy M1 bid/ask (dépôt privé forex-data). Bougies supérieures reconstruites à partir du M1.
Exécution : signal lu à la clôture d'une bougie, entrée à l'ouverture de la suivante (achat à l'ask, vente au bid) ;
stops / objectifs / trailing / sorties à heure fixe vérifiés minute par minute ; stop prioritaire si stop et objectif
tombent dans la même minute. Une position à la fois par stratégie et par paire.
"""
from __future__ import annotations

import gzip
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

PERIODS = ["2024sep-2025feb", "2025mar-aug", "2025sep-2026feb", "2026mar-aug"]


def pip(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def load_m1(data_dir: Path, symbol: str, periods=PERIODS) -> pd.DataFrame:
    frames = []
    for p in periods:
        f = Path(data_dir) / p / f"{symbol}.csv.gz"
        with gzip.open(f, "rt") as fh:
            df = pd.read_csv(fh)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.drop_duplicates("time").sort_values("time").set_index("time")
    return df[["bid_open", "bid_high", "bid_low", "bid_close", "ask_open", "ask_high", "ask_low", "ask_close"]].astype(float)


def resample(m1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    agg = {"bid_open": "first", "bid_high": "max", "bid_low": "min", "bid_close": "last",
           "ask_open": "first", "ask_high": "max", "ask_low": "min", "ask_close": "last"}
    out = m1.resample(f"{minutes}min", label="left", closed="left").agg(agg).dropna()
    out.columns = ["open", "high", "low", "close", "a_open", "a_high", "a_low", "a_close"]
    return out


@dataclass
class Rules:
    sl_pips: float | None = None          # stop initial (pips)
    tp_pips: float | None = None          # objectif (pips)
    trail_pips: float | None = None       # trailing stop (pips), activé quand le gain dépasse cette distance
    max_bars: int | None = None           # sortie après N bougies du timeframe
    cap_min: int | None = None            # sortie au plus tard après N minutes
    flat_utc_hour: int | None = None      # tout fermer à cette heure UTC
    entry_hours_utc: tuple | None = None  # (début, fin) : entrées autorisées si heure d'ouverture dans [début, fin[
    weekdays_only: bool = False


@dataclass
class Trade:
    pair: str
    side: int
    entry_time: pd.Timestamp
    entry: float
    exit_time: pd.Timestamp
    exit: float
    reason: str
    pips: float = field(default=0.0)


class Simulator:
    def __init__(self, symbol: str, m1: pd.DataFrame):
        self.symbol, self.p = symbol, pip(symbol)
        self.t = m1.index
        self.tns = m1.index.as_unit("ns").asi8          # pandas 3 : unité explicite (ns)
        self.bo, self.bh, self.bl, self.bc = (m1[c].to_numpy() for c in ("bid_open", "bid_high", "bid_low", "bid_close"))
        self.ao, self.ah, self.al, self.ac = (m1[c].to_numpy() for c in ("ask_open", "ask_high", "ask_low", "ask_close"))

    def idx(self, ts: pd.Timestamp) -> int:
        return int(np.searchsorted(self.tns, ts.value, side="left"))

    def _deadline(self, entry_time: pd.Timestamp, rules: Rules, tf_min: int | None) -> int:
        """Instant (ns) où la position doit être fermée au plus tard (ouverture de la minute concernée)."""
        d = np.iinfo(np.int64).max
        if rules.max_bars and tf_min:
            d = min(d, (entry_time + pd.Timedelta(minutes=rules.max_bars * tf_min)).value)
        if rules.cap_min:
            d = min(d, (entry_time + pd.Timedelta(minutes=rules.cap_min)).value)
        if rules.flat_utc_hour is not None:
            flat = entry_time.normalize() + pd.Timedelta(hours=rules.flat_utc_hour)
            if flat <= entry_time:
                flat += pd.Timedelta(days=1)
            d = min(d, flat.value)
        return d

    def run_position(self, side: int, entry_time: pd.Timestamp, rules: Rules, tf_min: int | None = None,
                     exit_times: np.ndarray | None = None, hard_exit: pd.Timestamp | None = None) -> Trade | None:
        j = self.idx(entry_time)
        n = len(self.tns)
        if j >= n:
            return None
        if self.tns[j] - entry_time.value > 3 * 3600 * 10**9:   # trou de données (week-end) : pas d'entrée
            return None
        entry = self.ao[j] if side > 0 else self.bo[j]
        sl = entry - side * rules.sl_pips * self.p if rules.sl_pips else None
        tp = entry + side * rules.tp_pips * self.p if rules.tp_pips else None
        deadline = self._deadline(pd.Timestamp(self.tns[j], tz="UTC"), rules, tf_min)
        if hard_exit is not None:
            deadline = min(deadline, hard_exit.value)
        sig_at = np.iinfo(np.int64).max                 # 1re bougie de sortie sur signal après l'entrée
        if exit_times is not None and len(exit_times):
            q = int(np.searchsorted(exit_times, self.tns[j], side="right"))
            if q < len(exit_times):
                sig_at = int(exit_times[q])
        k = j
        while k < n:
            ts = self.tns[k]
            if k > j:
                if ts >= deadline or ts >= sig_at:
                    px = self.bo[k] if side > 0 else self.ao[k]
                    return self._close(side, j, entry, k, px, "temps" if ts >= deadline else "signal")
            # stop / objectif dans la minute k (prix de sortie : bid pour un achat, ask pour une vente)
            if side > 0:
                lo, hi, op = self.bl[k], self.bh[k], self.bo[k]
                if sl is not None and lo <= sl:
                    return self._close(side, j, entry, k, min(op, sl) if k > j else sl, "stop")
                if tp is not None and hi >= tp:
                    return self._close(side, j, entry, k, max(op, tp) if k > j else tp, "objectif")
                if rules.trail_pips and self.bc[k] - entry > rules.trail_pips * self.p:
                    ns = self.bc[k] - rules.trail_pips * self.p
                    sl = ns if sl is None or ns > sl else sl
            else:
                lo, hi, op = self.al[k], self.ah[k], self.ao[k]
                if sl is not None and hi >= sl:
                    return self._close(side, j, entry, k, max(op, sl) if k > j else sl, "stop")
                if tp is not None and lo <= tp:
                    return self._close(side, j, entry, k, min(op, tp) if k > j else tp, "objectif")
                if rules.trail_pips and entry - self.ac[k] > rules.trail_pips * self.p:
                    ns = self.ac[k] + rules.trail_pips * self.p
                    sl = ns if sl is None or ns < sl else sl
            k += 1
        return None   # position encore ouverte en fin de données : ignorée

    def _close(self, side, j, entry, k, px, reason) -> Trade:
        return Trade(self.symbol, side, pd.Timestamp(self.tns[j], tz="UTC"), entry, pd.Timestamp(self.tns[k], tz="UTC"),
                     px, reason, side * (px - entry) / self.p)


def run_bar_strategy(sim: Simulator, bars: pd.DataFrame, long_sig, short_sig, rules: Rules, tf_min: int,
                     exit_long=None, exit_short=None) -> list[Trade]:
    """Signaux évalués à la clôture de la bougie i → entrée à l'ouverture de la bougie i+1."""
    idx = bars.index
    starts = idx.as_unit("ns").asi8
    ex_l = np.sort(starts[1:][np.asarray(exit_long, dtype=bool)[:-1]]) if exit_long is not None else None
    ex_s = np.sort(starts[1:][np.asarray(exit_short, dtype=bool)[:-1]]) if exit_short is not None else None
    L, S = np.asarray(long_sig), np.asarray(short_sig)
    trades, busy_until = [], -1
    for i in range(len(idx) - 1):
        if not (L[i] ^ S[i]):
            continue
        t_in = idx[i + 1]
        if t_in.value <= busy_until:
            continue
        if rules.weekdays_only and t_in.weekday() >= 5:
            continue
        if rules.entry_hours_utc and not (rules.entry_hours_utc[0] <= t_in.hour < rules.entry_hours_utc[1]):
            continue
        side = 1 if L[i] else -1
        tr = sim.run_position(side, t_in, rules, tf_min, ex_l if side > 0 else ex_s)
        if tr is None:
            continue
        trades.append(tr)
        busy_until = tr.exit_time.value
    return trades


# ---------------- indicateurs (définitions MetaTrader) ----------------
def ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False).mean()


def sma(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n).mean()


def smma(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(alpha=1 / n, adjust=False).mean()


def rsi(price: pd.Series, n: int) -> pd.Series:
    d = price.diff()
    up, dn = smma(d.clip(lower=0), n), smma((-d).clip(lower=0), n)
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def cci(b: pd.DataFrame, n: int) -> pd.Series:
    tp = (b["high"] + b["low"] + b["close"]) / 3
    m = sma(tp, n)
    md = tp.rolling(n).apply(lambda w: np.mean(np.abs(w - w.mean())), raw=True)
    return (tp - m) / (0.015 * md)


def wpr(b: pd.DataFrame, n: int) -> pd.Series:
    hh, ll = b["high"].rolling(n).max(), b["low"].rolling(n).min()
    return -100 * (hh - b["close"]) / (hh - ll)


def stochastic(b: pd.DataFrame, k: int, d: int, slowing: int, method: str = "ema"):
    ll, hh = b["low"].rolling(k).min(), b["high"].rolling(k).max()
    main = 100 * (b["close"] - ll).rolling(slowing).sum() / (hh - ll).rolling(slowing).sum()
    sig = ema(main, d) if method == "ema" else sma(main, d)
    return main, sig


def bands(price: pd.Series, n: int, dev: float):
    m = sma(price, n)
    sd = price.rolling(n).std(ddof=0)
    return m - dev * sd, m, m + dev * sd


def macd(close: pd.Series, fast=12, slow=26, signal=9):
    main = ema(close, fast) - ema(close, slow)
    return main, sma(main, signal)          # MetaTrader : ligne de signal = SMA


def change_in_pct(v1: pd.Series, v2: pd.Series) -> pd.Series:
    """Math::ChangeInPct(v1, v2, true) d'EA31337 (en %), signe selon v2 > v1."""
    r = (v2 / v1) - 1
    r = r.where((v1 != 0) & (v2 != 0), np.where((v1 == 0) & (v2 == 0), 0.0, 1.0))
    return np.where(v2 > v1, np.abs(r), -np.abs(r)) * 100
