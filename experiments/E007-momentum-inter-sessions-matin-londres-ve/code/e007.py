"""E007 - momentum inter-sessions (matin Londres -> 13:00-17:00). Règles : ../protocol.md (verrouillé).
Réutilise en LECTURE SEULE research/v4 (data._read, bars, atr, PIP ; sim.Market, simulate) et research/common/robustness."""
from __future__ import annotations

import sys
from datetime import datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from research.v4.data import PIP, _read, atr, bars  # noqa: E402
from research.v4.sim import Market, simulate  # noqa: E402
from research.common import robustness as rb  # noqa: E402

LON = ZoneInfo("Europe/London")
PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
STOP_ATR = 3.0
MIN_PRESENT = 0.90
TOL_MIN = 5
USD_SIGN = {"EURUSD": -1, "GBPUSD": -1, "USDJPY": +1}   # sens du trade -> sens USD = sign * dir
EXCLUDE_MD = {(12, 24), (12, 25), (12, 26), (12, 31), (1, 1)}
FOMC = {"2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29"}
DST_DAYS = {"2025-10-27", "2025-10-28", "2025-10-29", "2025-10-30", "2025-10-31"}
WINDOWS = {
    "train": dict(dirs=["m1_2025"], start="2025-09-02", end="2026-03-01"),
    "validation": dict(dirs=["m1"], start="2026-03-02", end="2026-09-01"),
}
# variantes : (heure locale d'entrée, heures de signal en amont, hold min, filtre médiane)
VARIANTS = {"A": (13.0, 5.0, 240, False), "B": (13.0, 5.0, 240, True), "C": (13.0, 5.0, 120, False),
            "D": (13.0, 6.0, 240, False)}
SHIFTS = [k for k in range(-8, 9) if k != 0]


def local_to_utc(d, hour: float) -> pd.Timestamp:
    dt = datetime.combine(d, dtime(int(hour), int(round((hour - int(hour)) * 60))), tzinfo=LON)
    return pd.Timestamp(dt).tz_convert("UTC")


def load_window(name: str) -> dict:
    w = WINDOWS[name]
    miss = [str(ROOT / "data" / d / f"{s}.csv") for d in w["dirs"] for s in PAIRS
            if not (ROOT / "data" / d / f"{s}.csv").exists()]
    if miss:
        raise SystemExit("DONNEES ABSENTES : " + ", ".join(miss))
    return {s: _read([ROOT / "data" / d for d in w["dirs"]], s) for s in PAIRS}


class Pair:
    def __init__(self, df, sym):
        self.sym, self.df, self.market = sym, df, Market(df)
        a = atr(bars(df, "1h"), 14)
        a.index = a.index + pd.Timedelta(hours=1)        # disponible à la fin de la barre H1
        self.atr = a
        self.t = df.index.values
        self.mid = df["mid"]

    def mid_at(self, ts):
        """Clôture mid de la dernière minute < ts (donc connue avant ts), tolérance 5 min."""
        t = (ts - pd.Timedelta(minutes=1))
        i = self.mid.index.searchsorted(t, side="right") - 1
        if i < 0 or (t - self.mid.index[i]) > pd.Timedelta(minutes=TOL_MIN):
            return np.nan
        return float(self.mid.iloc[i])


def days_of(w):
    return [d.date() for d in pd.bdate_range(w["start"], pd.Timestamp(w["end"]) - pd.Timedelta(days=1))
            if (d.month, d.day) not in EXCLUDE_MD]


def raw_signals(p: Pair, w: dict, entry_h: float, back_h: float, hold: int) -> pd.DataFrame:
    """Un signal par jour ouvré : S = mid(entrée) - mid(entrée - back_h). Sans R."""
    rows = []
    for d in days_of(w):
        t0 = local_to_utc(d, entry_h)
        ts = t0 - pd.Timedelta(hours=back_h)
        t1 = t0 + pd.Timedelta(minutes=hold)
        if t1.date() != t0.date() or t1.hour * 60 + t1.minute > 21 * 60 or ts.date() != t0.date():
            continue
        a = p.atr.asof(t0)
        i0 = np.searchsorted(p.t, np.datetime64(t0.tz_localize(None)))
        j1 = np.searchsorted(p.t, np.datetime64(t1.tz_localize(None)))
        s = p.mid_at(t0) - p.mid_at(ts)
        if not (np.isfinite(a) and a > 0 and np.isfinite(s)) or (j1 - i0) < MIN_PRESENT * hold or s == 0:
            continue
        rows.append((t0, p.sym, int(np.sign(s)), abs(float(s)), float(a), hold, d))
    return pd.DataFrame(rows, columns=["time", "sym", "dir", "absS", "atr", "hold", "day"])


def signals(P: dict, w: dict, vid: str = "A", shift: int = 0, fade: bool = False) -> pd.DataFrame:
    entry_h, back_h, hold, med = VARIANTS[vid]
    parts = []
    for s, p in P.items():
        g = raw_signals(p, w, entry_h + shift, back_h, hold)
        if med and len(g):
            m = g["absS"].shift(1).rolling(20, min_periods=20).median()   # 20 signaux précédents seulement
            g = g[(g["absS"] >= m) & m.notna()]
        parts.append(g)
    sig = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if fade and len(sig):
        sig["dir"] = -sig["dir"]
    return sig


def fixed_usd(P: dict, w: dict, usd: int) -> pd.DataFrame:
    """Contrôle E005 : 13:00 -> 17:00 USD long (usd=+1) ou court (-1) fixe, mêmes jours/filtres que A."""
    sig = signals(P, w, "A")
    sig = sig.copy()
    sig["dir"] = usd * sig["sym"].map(USD_SIGN)
    return sig


def simulate_trades(P: dict, sig: pd.DataFrame) -> pd.DataFrame:
    out = []
    for s, g in sig.groupby("sym"):
        g = g.reset_index(drop=True)
        stop = STOP_ATR * g["atr"]
        res = simulate(P[s].market, g["time"], g["dir"], stop, np.full(len(g), np.inf),
                       hold=int(g["hold"].iloc[0]), max_gap_min=1)
        x = g.join(res)
        x["stop"] = stop
        x["pips"] = x["r"] * x["stop"] / PIP[s]
        out.append(x)
    if not out:
        return pd.DataFrame(columns=list(sig.columns) + ["r", "stop", "pips", "exit"])
    return pd.concat(out, ignore_index=True).dropna(subset=["r"]).sort_values(["time", "sym"]).reset_index(drop=True)


def trades(P, w, vid="A", shift=0, fade=False):
    return simulate_trades(P, signals(P, w, vid, shift, fade))


def day_stats(t):
    d = t.groupby("day")["r"].sum() if len(t) else pd.Series(dtype=float)
    n = len(d)
    sd = d.std(ddof=1) if n > 1 else np.nan
    return {"days": n, "mean_day_sum": float(d.mean()) if n else np.nan,
            "t": float(d.mean() / (sd / np.sqrt(n))) if n > 1 and sd > 0 else np.nan}
