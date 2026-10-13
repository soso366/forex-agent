"""E008 - epuisement du range journalier : fade a 13:00 Londres, sortie 17:00 Londres. Regles : ../protocol.md.
Reutilise en LECTURE SEULE research/v4 (data._read, bars, atr, PIP ; sim.Market, simulate) et research/common/robustness.

Conventions : index UTC = debut de minute. Jour = date calendaire Europe/London (zoneinfo, DST gere). mid = (bid+ask)/2.
M = (mid_open(signal) - mid_open(00:00 Londres)) / ADR20 ; mid_open(signal) = OPEN de la barre M1 d'entree (connu a l'instant d'entree).
ADR20 = moyenne des (high-low) mid des 20 jours Londres valides PRECEDENTS (jour courant exclu, >= 10 requis).
ATR M5(14) : derniere barre dont la FIN est <= signal (label signal-5min).
"""
from __future__ import annotations

import sys
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

PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
LONDON = ZoneInfo("Europe/London")
STOP_ATR = 3.0
N_MIN = 150
COSTS = (0.0, 0.2, 0.5, 1.0)
SHIFTS = (-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6)
N_RAND = 1000
CUTOFF_UTC_MIN = 20 * 60 + 55          # sortie au plus tard 20:55 UTC (placebos decales)
# id : (heure signal/entree Londres, seuil |M|, hold min)
VARIANTS = {"A": (13, 0.30, 240), "B": (13, 0.40, 240), "C": (13, 0.30, 120), "D": (12, 0.30, 240)}
SPLITS = {"train": ("2025-09-01", "2026-03-01"), "validation": ("2026-03-01", "2026-09-01")}
SRC = {"train": ["m1_2025"], "validation": ["m1_2025", "m1"]}   # validation : m1_2025 charge pour l'echauffement ADR


def load(split):
    out = {}
    for s in PAIRS:
        for d in SRC[split]:
            p = ROOT / "data" / d / f"{s}.csv"
            if not p.exists():
                raise SystemExit(f"DONNEES ABSENTES : {p}")
        out[s] = _read([ROOT / "data" / d for d in SRC[split]], s)
    return out


def london_ts(day, hour):
    return pd.Timestamp(f"{day:%Y-%m-%d} {hour:02d}:00", tz=LONDON).tz_convert("UTC")


class Pair:
    def __init__(self, df, sym):
        self.sym, self.pip, self.df = sym, PIP[sym], df
        self.mkt = Market(df)
        self.day0 = df.index[0].floor("D")
        n = (df.index[-1].floor("D") - self.day0).days + 2
        g = pd.date_range(self.day0, periods=n * 1440, freq="1min", tz="UTC")
        x = df.reindex(g)
        self.grid0, self.n = g[0], len(g)
        self.mo = ((x["bo"] + x["ao"]) / 2).to_numpy()
        self.mh = ((x["bh"] + x["ah"]) / 2).to_numpy()
        self.ml = ((x["bl"] + x["al"]) / 2).to_numpy()
        a = atr(bars(df, "5min"), 14)
        self.atr = {t: v for t, v in zip(a.index, a.to_numpy())}
        self.days = [d.date() for d in pd.date_range(self.day0.tz_localize(None) - pd.Timedelta(days=1),
                                                     periods=n + 2, freq="D")]
        self._rng = {}

    def i(self, ts):
        return int((ts - self.grid0) // pd.Timedelta(minutes=1))

    def _at(self, ts):
        i = self.i(ts)
        if i < 0 or i + 3 > self.n:
            return np.nan
        for j in range(3):
            if np.isfinite(self.mo[i + j]):
                return self.mo[i + j]
        return np.nan

    def day_range(self, d):
        """high-low mid du jour Londres d (00:00 -> 00:00 Londres suivant) ; NaN si < 1000 minutes."""
        if d in self._rng:
            return self._rng[d]
        a, b = self.i(london_ts(d, 0)), self.i(london_ts(d + pd.Timedelta(days=1), 0))
        v = np.nan
        if a >= 0 and b <= self.n:
            h, l = self.mh[a:b], self.ml[a:b]
            if np.isfinite(h).sum() >= 1000:
                v = np.nanmax(h) - np.nanmin(l)
        self._rng[d] = v
        return v

    def adr20(self, d):
        """Moyenne des 20 derniers jours valides STRICTEMENT avant d (le jour d n'est jamais lu)."""
        prev, k = [], 1
        while len(prev) < 20 and k <= 60:
            r = self.day_range(d - pd.Timedelta(days=k))
            if np.isfinite(r):
                prev.append(r)
            k += 1
        return (float(np.mean(prev)) if len(prev) >= 10 else np.nan)

    def events(self, hour, d_from, d_to):
        """Une ligne par jour ouvre Londres de [d_from, d_to) : M, ATR, tout connu a l'instant de signal."""
        rows = []
        for d in pd.date_range(d_from, d_to, freq="D", inclusive="left"):
            if d.weekday() > 4:
                continue
            d = d.date()
            d = pd.Timestamp(d)
            t0, ts = london_ts(d, 0), london_ts(d, int(hour))
            p0, ps = self._at(t0), self._at(ts)
            a_ = self.atr.get(ts - pd.Timedelta(minutes=5), np.nan)
            adr = self.adr20(d)
            if not (np.isfinite(p0) and np.isfinite(ps) and np.isfinite(a_) and a_ > 0 and np.isfinite(adr) and adr > 0):
                continue
            rows.append(dict(day=d.normalize(), sym=self.sym, ts=ts, hour=int(hour), M=(ps - p0) / adr, atr=a_, adr=adr,
                             utc1=bool(ts.hour == 12)))     # 13:00 Londres = 12:00 UTC en heure d'ete
        return pd.DataFrame(rows)


def select(ev, thr):
    return ev[ev["M"].abs() >= thr]


def sim_events(P, ev, hold, direction=+1, cap=False):
    """direction=+1 : fade (contre M) ; -1 : continuation. Entree open M1 du signal, stop 3 ATR, sortie temps (close M1)."""
    if len(ev) == 0:
        return pd.DataFrame()
    ev = ev.reset_index(drop=True)
    d = -np.sign(ev["M"].to_numpy()) * direction
    sd = STOP_ATR * ev["atr"].to_numpy()
    holds = np.full(len(ev), float(hold))
    if cap:
        um = (ev["ts"].dt.hour * 60 + ev["ts"].dt.minute).to_numpy()
        holds = np.minimum(holds, CUTOFF_UTC_MIN - um)
    s = pd.DataFrame(index=range(len(ev)), columns=["r", "mfe_r", "mae_r", "exit", "minutes"])
    for h in np.unique(holds):
        m = holds == h
        if h <= 0:
            s.loc[m, "exit"] = "skip"
            continue
        part = simulate(P.mkt, ev.loc[m, "ts"], d[m], sd[m], np.full(m.sum(), np.inf), hold=int(h), max_gap_min=1)
        s.loc[m, :] = part.to_numpy()
    s = s.astype({"r": float, "mfe_r": float, "mae_r": float, "minutes": float})
    t = pd.concat([ev, s], axis=1)
    t["time"] = t["ts"]
    t["dir"] = d
    t["stop"] = sd
    t = t[t["exit"] != "skip"].reset_index(drop=True)
    assert ((t["time"] + pd.to_timedelta(t["minutes"], unit="m")).dt.hour.max() < 21)
    return t


def day_series(t):
    return t.groupby("day")["r"].mean()


def day_stats(t, n_boot=10000, seed=11):
    d = day_series(t)
    n = len(d)
    if n < 2:
        return dict(days=n, mean=np.nan, t=np.nan, ci95=[np.nan, np.nan])
    sd = d.std(ddof=1)
    rng = np.random.default_rng(seed)
    b = rng.choice(d.to_numpy(), (n_boot, n)).mean(axis=1)
    return dict(days=int(n), mean=float(d.mean()), t=float(d.mean() / (sd / np.sqrt(n))) if sd > 0 else np.nan,
                ci95=[float(np.quantile(b, .025)), float(np.quantile(b, .975))])


def cost_stats(t, extra):
    return rb.stats(t["r"] - extra * t["sym"].map(PIP) / t["stop"])
