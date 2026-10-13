"""E009 - retard de USDJPY sur le facteur dollar (EURUSD, GBPUSD). Regles : ../protocol.md.
Reutilise en LECTURE SEULE research/v4 (data._read, bars, atr, PIP ; sim.Market, simulate) et research/common/robustness.

Conventions : index UTC = debut de minute. Barre M5 label L = [L, L+5min) ; le signal est evalue a la CLOTURE tc = L+5min
(la barre L est terminee), entree a l'open M1 de tc. mid = (bid+ask)/2 ; rendement 30 min = log(c[L]) - log(c[L-30min]).
sigma de g = ecart-type des 2000 observations PRECEDENTES (rolling(2000).std().shift(1)).
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

LONDON = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")
SYM = "USDJPY"
LEGS = ("EURUSD", "GBPUSD")
STOP_ATR = 3.0
N_MIN = 150
SIG_WIN = 2000
COSTS = (0.0, 0.2, 0.5, 1.0)
SHIFTS = (-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6)
N_PERM = 500
CUTOFF_UTC_MIN = 20 * 60 + 55
MIN_HOLD = 30
# id : (seuil |z|, hold min)
VARIANTS = {"A": (2.0, 120), "B": (2.0, 60), "C": (2.0, 240), "D": (2.5, 120)}
COOLDOWN = 120
MAX_PER_DAY = 2
SPLITS = {"train": ("2025-09-01", "2026-03-01"), "validation": ("2026-03-01", "2026-09-01")}
SRC = {"train": ["m1_2025"], "validation": ["m1_2025", "m1"]}


def load(split):
    out = {}
    for s in (SYM,) + LEGS:
        for d in SRC[split]:
            p = ROOT / "data" / d / f"{s}.csv"
            if not p.exists():
                raise SystemExit(f"DONNEES ABSENTES : {p}")
        out[s] = _read([ROOT / "data" / d for d in SRC[split]], s)
    return out


def london_ts(day, hour, minute=0):
    return pd.Timestamp(f"{pd.Timestamp(day):%Y-%m-%d} {hour:02d}:{minute:02d}", tz=LONDON).tz_convert("UTC")


def m5_close(df):
    b = bars(df, "5min")
    return b["c"], b


def ret30(c, grid):
    x = np.log(c.reindex(grid))
    return x - x.shift(6)


def zscore(g, win=SIG_WIN):
    gs = g.dropna()
    sig = gs.rolling(win, min_periods=win).std().shift(1)
    return (gs / sig).dropna()


def zscore_hour(g, win=240):
    """Diagnostic : sigma conditionnel a l'heure Londres de la barre (240 obs. precedentes de la meme heure)."""
    gs = g.dropna()
    h = gs.index.tz_convert(LONDON).hour
    sig = gs.groupby(h).transform(lambda x: x.rolling(win, min_periods=win).std().shift(1))
    return (gs / sig).dropna()


class Data:
    def __init__(self, raw):
        self.raw = raw
        cs = {s: m5_close(raw[s]) for s in raw}
        self.bars_j = cs[SYM][1]
        idx = cs[SYM][0].index.union(cs[LEGS[0]][0].index).union(cs[LEGS[1]][0].index)
        self.grid = pd.date_range(idx[0], idx[-1], freq="5min", tz="UTC")
        self.r = {s: ret30(cs[s][0], self.grid) for s in raw}
        self.usd = -(self.r[LEGS[0]] + self.r[LEGS[1]]) / 2
        self.g = self.r[SYM] - self.usd
        self.g_alone = self.r[SYM]                         # placebo "USDJPY seul"
        self.z = zscore(self.g)
        a = atr(self.bars_j, 14)
        self.atr = a
        self.mkt = Market(raw[SYM])
        df = raw[SYM]
        g1 = pd.date_range(df.index[0].floor("D"), df.index[-1].floor("D") + pd.Timedelta(days=2), freq="1min", tz="UTC")
        x = df.reindex(g1)
        self.g1 = g1
        self.mo = ((x["bo"] + x["ao"]) / 2).to_numpy()
        self.mc = x["mid"].to_numpy()

    def i1(self, ts):
        return int((ts - self.g1[0]) // pd.Timedelta(minutes=1))


def build_events(z, atr_s, thr, hold, shift_h=0, win=(8, 15), exit_h=17):
    """Selection chronologique : |z|>=thr, tc dans [win0+s, win1+s) heure Londres, cooldown, <=2/jour, une position.
    Renvoie un DataFrame (une ligne = un trade) avec ts d'entree, M1-hold effectif, z, sens (fade), atr connu."""
    cand = z[z.abs() >= thr]
    rows, last_free, per_day = [], None, {}
    for L, zv in cand.items():
        tc = L + pd.Timedelta(minutes=5)
        lt = tc.tz_convert(LONDON)
        hm = lt.hour + lt.minute / 60
        if not (win[0] + shift_h <= hm < win[1] + shift_h):
            continue
        day = lt.normalize().tz_localize(None)
        if per_day.get(day, 0) >= MAX_PER_DAY or (last_free is not None and tc < last_free):
            continue
        end_cap = min((london_ts(day, exit_h + shift_h) - tc).total_seconds() / 60,
                      CUTOFF_UTC_MIN - (tc.hour * 60 + tc.minute))
        h = min(hold, end_cap)
        if h < MIN_HOLD and shift_h == 0:
            continue
        if h < MIN_HOLD:
            continue
        a_ = atr_s.get(L, np.nan)
        if not (np.isfinite(a_) and a_ > 0):
            continue
        rows.append(dict(day=day, ts=tc, hold=float(h), z=float(zv), atr=float(a_), hour=int(lt.hour), dir=-int(np.sign(zv))))
        per_day[day] = per_day.get(day, 0) + 1
        last_free = tc + pd.Timedelta(minutes=max(COOLDOWN, hold))
    return pd.DataFrame(rows)


def sim_events(D, ev, direction=+1):
    """direction=+1 fade (contre z) ; -1 continuation. Stop 3 ATR M5(14), 1 R = 3 ATR, sortie temps close M1."""
    if len(ev) == 0:
        return pd.DataFrame()
    ev = ev.reset_index(drop=True)
    d = ev["dir"].to_numpy() * direction
    sd = STOP_ATR * ev["atr"].to_numpy()
    s = pd.DataFrame(index=range(len(ev)), columns=["r", "mfe_r", "mae_r", "exit", "minutes"])
    for h in np.unique(ev["hold"]):
        m = (ev["hold"] == h).to_numpy()
        part = simulate(D.mkt, ev.loc[m, "ts"], d[m], sd[m], np.full(m.sum(), np.inf), hold=int(h), max_gap_min=1)
        s.loc[m, :] = part.to_numpy()
    s = s.astype({"r": float, "mfe_r": float, "mae_r": float, "minutes": float})
    t = pd.concat([ev, s], axis=1)
    t["time"] = t["ts"]
    t["sym"] = SYM
    t["stop"] = sd
    t["dir"] = d
    t = t[t["exit"] != "skip"].dropna(subset=["r"]).reset_index(drop=True)
    if len(t):
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
    return rb.stats(t["r"] - extra * PIP[SYM] / t["stop"])
