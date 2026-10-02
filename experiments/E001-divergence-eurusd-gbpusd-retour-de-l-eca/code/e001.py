"""E001 — divergence EURUSD/GBPUSD : retour de l'écart EURGBP implicite.

Règles : voir ../protocol.md (verrouillé). Réutilise research/v4/data.py (_read, bars, atr) en lecture seule.
Le simulateur reprend les conventions de research/v4/sim.py (entrée à l'ouverture, stop prioritaire, glissement à
l'ouverture, sortie au temps à la clôture) et y ajoute la sortie anticipée |z| <= 0,5 (sortie à l'ouverture suivante).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.v4.data import _read, atr, bars  # noqa: E402

TZ = "Europe/London"
PAIRS = ("EURUSD", "GBPUSD")
S_START, S_END = pd.Timedelta(hours=7), pd.Timedelta(hours=16, minutes=30)
FFILL = 2
COOLDOWN = pd.Timedelta(minutes=30)
STOP_ATR = 1.5
U_MAX = 1.0
SPREAD_MULT = 2.0
Z_EXIT = 0.5
NDAYS = 20

VARIANTS = {
    "V1": dict(thr=2.5, W=15, H=20), "V2": dict(thr=2.5, W=15, H=30),
    "V3": dict(thr=2.5, W=30, H=20), "V4": dict(thr=2.5, W=30, H=30),
    "V5": dict(thr=3.0, W=15, H=20), "V6": dict(thr=3.0, W=15, H=30),
    "V7": dict(thr=3.0, W=30, H=20), "V8": dict(thr=3.0, W=30, H=30),
}


def neighbors(vid: str) -> list[str]:
    v = VARIANTS[vid]
    out = []
    for k, w in VARIANTS.items():
        if k != vid and sum(v[d] != w[d] for d in ("thr", "W", "H")) == 1:
            out.append(k)
    return out


WINDOWS = {
    "train": dict(dirs=["m1_2025"], start="2025-09-01", end="2026-03-01"),
    "valA": dict(dirs=["m1_2025", "m1"], start="2026-03-01", end="2026-09-01"),
    "valB": dict(dirs=["m1_locked_2024", "m1_locked"], start="2024-09-01", end="2025-09-01"),
}

# Diagnostic uniquement (aucun filtre). BCE et BoE : calendriers publics connus ; 2026 = calendrier annoncé.
ECB = ["2024-09-12", "2024-10-17", "2024-12-12", "2025-01-30", "2025-03-06", "2025-04-17", "2025-06-05",
       "2025-07-24", "2025-09-11", "2025-10-30", "2025-12-18", "2026-02-05", "2026-03-19", "2026-04-30",
       "2026-06-11", "2026-07-23"]
BOE = ["2024-09-19", "2024-11-07", "2024-12-19", "2025-02-06", "2025-03-20", "2025-05-08", "2025-06-19",
       "2025-08-07", "2025-09-18", "2025-11-06", "2025-12-18", "2026-02-05", "2026-03-19", "2026-04-30",
       "2026-06-18", "2026-07-30"]


def news_days(start="2023-09-01", end="2026-09-01") -> set:
    d = pd.date_range(start, end, freq="D")
    nfp = d[(d.weekday == 4) & (d.day <= 7)]
    return set(pd.DatetimeIndex(nfp).date) | {pd.Timestamp(x).date() for x in ECB + BOE}


NEWS_DAYS = news_days()


# ----------------------------------------------------------------------------------------------- données
def load_window(name: str) -> dict:
    w = WINDOWS[name]
    return {s: _read([ROOT / "data" / d for d in w["dirs"]], s) for s in PAIRS}


class Features:
    """Tout ce qui est calculé à la minute t n'utilise que des minutes <= t (σ et médianes : jours < J)."""

    def __init__(self, raw: dict, W: int):
        self.W = W
        self.raw = raw
        lo = max(raw[s].index[0] for s in PAIRS)
        hi = min(raw[s].index[-1] for s in PAIRS)
        grid = pd.date_range(lo, hi, freq="1min", tz="UTC")
        self.grid = grid
        mid = {s: raw[s]["mid"].reindex(grid).ffill(limit=FFILL) for s in PAIRS}
        spr = {s: raw[s]["spread"].reindex(grid).ffill(limit=FFILL) for s in PAIRS}
        self.mid, self.spr = mid, spr
        lE, lG = np.log(mid["EURUSD"]), np.log(mid["GBPUSD"])
        self.rE, self.rG = lE - lE.shift(W), lG - lG.shift(W)
        self.dE = mid["EURUSD"] - mid["EURUSD"].shift(W)
        self.dG = mid["GBPUSD"] - mid["GBPUSD"].shift(W)
        self.x = self.rE - self.rG
        self.u = (self.rE + self.rG) / 2
        loc = grid.tz_convert(TZ)
        self.day = pd.Series(loc.tz_localize(None).normalize(), index=grid)
        tod = loc.tz_localize(None) - loc.tz_localize(None).normalize()
        self.in_session = pd.Series((tod >= S_START) & (tod <= S_END) & (loc.weekday < 5), index=grid)
        self.scan = self.in_session & pd.Series(grid.minute % 5 == 0, index=grid)
        self._day_stats()
        self.atr = {s: self._atr(s) for s in PAIRS}

    def _atr(self, s):
        m5 = bars(self.raw[s], "5min")
        a = atr(m5)
        a.index = a.index + pd.Timedelta(minutes=5)          # ATR connu à la CLÔTURE de la M5
        return a.reindex(self.grid, method="ffill")          # à t : dernière M5 clôturée <= t

    def _day_stats(self):
        W = self.W
        days = sorted(self.day[self.in_session].unique())
        per_day = {}
        lE, lG = np.log(self.mid["EURUSD"]), np.log(self.mid["GBPUSD"])
        for d in days:
            d0 = pd.Timestamp(d).tz_localize(TZ)
            bounds = pd.date_range(d0 + S_START, d0 + S_END, freq=f"{W}min").tz_convert("UTC")
            bounds = bounds[(bounds >= self.grid[0]) & (bounds <= self.grid[-1])]
            if len(bounds) < 2:
                continue
            e, g = lE.reindex(bounds).to_numpy(), lG.reindex(bounds).to_numpy()
            re, rg = np.diff(e), np.diff(g)
            xb, ub = re - rg, (re + rg) / 2
            ok = np.isfinite(xb) & np.isfinite(ub)
            nblocks = int((S_END - S_START) / pd.Timedelta(minutes=W))
            if ok.sum() < 0.5 * nblocks:
                continue
            m = self.in_session & (self.day == d)
            sp = {s: self.raw[s]["spread"].reindex(self.grid[m.to_numpy()]).dropna().to_numpy() for s in PAIRS}
            per_day[d] = (xb[ok], ub[ok], sp)
        valid = sorted(per_day)
        self.valid_days = valid
        sx, su, med = {}, {s: {} for s in PAIRS}, {s: {} for s in PAIRS}
        sxd, sud = {}, {}
        all_days = sorted(self.day.unique())
        for d in all_days:
            prev = [v for v in valid if v < d][-NDAYS:]
            if len(prev) < NDAYS:
                continue
            xs = np.concatenate([per_day[v][0] for v in prev])
            us = np.concatenate([per_day[v][1] for v in prev])
            sxd[d], sud[d] = xs.std(ddof=1), us.std(ddof=1)
            for s in PAIRS:
                med[s][d] = float(np.median(np.concatenate([per_day[v][2][s] for v in prev])))
        self.sx = pd.Series(sxd, dtype=float)
        self.su = pd.Series(sud, dtype=float)
        self.med = {s: pd.Series(med[s], dtype=float) for s in PAIRS}

    def frame(self, lag: int = 0) -> pd.DataFrame:
        """Table des minutes de scan t ; lag > 0 : conditions lues à t − lag (placebo), σ du jour de t."""
        t = self.grid[self.scan.to_numpy()]
        src = t - pd.Timedelta(minutes=lag)
        day = self.day.reindex(t).to_numpy()
        sx = self.sx.reindex(day).to_numpy()
        su = self.su.reindex(day).to_numpy()
        f = pd.DataFrame(index=t)
        f["day"] = day
        f["x"] = self.x.reindex(src).to_numpy()
        f["z"] = f["x"] / sx
        f["uz"] = self.u.reindex(src).to_numpy() / su
        for s, d in (("EURUSD", self.dE), ("GBPUSD", self.dG)):
            f[f"d_{s}"] = d.reindex(src).to_numpy()
            f[f"atrsig_{s}"] = self.atr[s].reindex(src).to_numpy()
            f[f"atr_{s}"] = self.atr[s].reindex(t).to_numpy()
            f[f"spok_{s}"] = self.spr[s].reindex(src).to_numpy() <= SPREAD_MULT * self.med[s].reindex(day).to_numpy()
        f["mvE"] = (f["d_EURUSD"] / f["atrsig_EURUSD"]).abs()
        f["mvG"] = (f["d_GBPUSD"] / f["atrsig_GBPUSD"]).abs()
        f["spok"] = f["spok_EURUSD"] & f["spok_GBPUSD"]
        f["fautive"] = np.where(f["mvE"] >= f["mvG"], "EURUSD", "GBPUSD")
        f["move"] = np.maximum(f["mvE"], f["mvG"])
        return f


# ------------------------------------------------------------------------------------------ signaux
def candidates(f: pd.DataFrame, thr: float) -> pd.DataFrame:
    ok = (f["z"].abs() >= thr) & (f["uz"].abs() <= U_MAX) & f["spok"] & f["move"].notna()
    c = f[ok].copy()
    sx = np.sign(c["x"])
    conv = np.where(c["fautive"] == "EURUSD", -sx, sx)
    dleg = np.where(c["fautive"] == "EURUSD", c["d_EURUSD"], c["d_GBPUSD"])
    c["dir"] = conv
    c["coherent"] = conv == -np.sign(dleg)
    c["other"] = np.where(c["fautive"] == "EURUSD", "GBPUSD", "EURUSD")
    return c


def with_cooldown(c: pd.DataFrame, leg_col: str) -> pd.DataFrame:
    last = {}
    keep = []
    for i, (t, s) in enumerate(zip(c.index, c[leg_col])):
        e = t + pd.Timedelta(minutes=1)
        if s in last and e - last[s] < COOLDOWN:
            continue
        last[s] = e
        keep.append(i)
    return c.iloc[keep]


def make_trades(f: pd.DataFrame, thr: float, start, end, leg: str = "fautive") -> tuple[pd.DataFrame, dict]:
    c = candidates(f, thr)
    c = c[(c.index >= pd.Timestamp(start, tz="UTC")) & (c.index < pd.Timestamp(end, tz="UTC"))]
    info = {"raw_signals": int(len(c)), "incoherent_ignored": int((~c["coherent"]).sum())}
    c = c[c["coherent"]]
    if leg == "inverse":
        c = c.assign(sym=c["other"], dir=np.where(c["other"] == "EURUSD", -np.sign(c["x"]), np.sign(c["x"])))
    else:
        c = c.assign(sym=c["fautive"])
    c = with_cooldown(c, "sym")
    tr = pd.DataFrame({"time": c.index + pd.Timedelta(minutes=1), "signal_time": c.index, "sym": c["sym"].to_numpy(),
                       "dir": c["dir"].astype(float).to_numpy(), "day": c["day"].to_numpy(),
                       "move": c["move"].to_numpy()})
    tr["stop"] = [STOP_ATR * f.at[t, f"atr_{s}"] for t, s in zip(c.index, tr["sym"])]
    return tr.reset_index(drop=True), info


# --------------------------------------------------------------------------------------- simulation
class Mkt:
    def __init__(self, df):
        self.t = df.index.tz_convert("UTC").tz_localize(None).values
        for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"):
            setattr(self, c, df[c].to_numpy())


def simulate_trades(feat: Features, tr: pd.DataFrame, H: int, early: bool = True, max_gap_min: int = 1) -> pd.DataFrame:
    tr = tr.copy()
    out_r, out_ex, out_min = [], [], []
    mk = {s: Mkt(feat.raw[s]) for s in PAIRS}
    gt = feat.grid.tz_localize(None).values
    zv = feat.x.to_numpy()
    for row in tr.itertuples(index=False):
        m = mk[row.sym]
        et = np.datetime64(pd.Timestamp(row.time).tz_convert("UTC").tz_localize(None))
        i = int(np.searchsorted(m.t, et))
        sd, d = row.stop, row.dir
        if i >= len(m.t) or not (sd > 0) or m.t[i] - et > np.timedelta64(max_gap_min, "m"):
            out_r.append(np.nan); out_ex.append("skip"); out_min.append(np.nan); continue
        j_end = int(np.searchsorted(m.t, m.t[i] + np.timedelta64(H, "m")))
        sxj = feat.sx.get(row.day, np.nan)
        px = m.ao[i] if d > 0 else m.bo[i]
        stop = px - sd if d > 0 else px + sd
        r, ex, mins = np.nan, None, np.nan
        for k in range(i, j_end):
            o = m.bo[k] if d > 0 else m.ao[k]
            hit = (m.bl[k] <= stop) if d > 0 else (m.ah[k] >= stop)
            if hit:
                ex, mins = "stop", k - i + 1
                gap = (d > 0 and o < stop) or (d < 0 and o > stop)
                r = d * (o - px) / sd if gap else -1.0
                break
            if early and k + 1 < j_end:
                g = int(np.searchsorted(gt, m.t[k]))
                if g < len(gt) and gt[g] == m.t[k]:
                    z = abs(zv[g] / sxj)
                    if np.isfinite(z) and z <= Z_EXIT:
                        o2 = m.bo[k + 1] if d > 0 else m.ao[k + 1]
                        r, ex, mins = d * (o2 - px) / sd, "early", k + 1 - i
                        break
        if ex is None:
            last = m.bc[j_end - 1] if d > 0 else m.ac[j_end - 1]
            r, ex, mins = d * (last - px) / sd, "time", j_end - i
        out_r.append(r); out_ex.append(ex); out_min.append(mins)
    tr["r"], tr["exit"], tr["minutes"] = out_r, out_ex, out_min
    return tr


# --------------------------------------------------------------------------------------- contrôles
def control_pool(feat: Features, f: pd.DataFrame, start, end, H: int, min_move: dict) -> pd.DataFrame:
    ok = (f["z"].abs() < 1.0) & f["spok"] & f["move"].notna()
    c = f[ok]
    c = c[(c.index >= pd.Timestamp(start, tz="UTC")) & (c.index < pd.Timestamp(end, tz="UTC"))]
    c = c[c["move"] >= c["fautive"].map(min_move).fillna(np.inf)]
    dleg = np.where(c["fautive"] == "EURUSD", c["d_EURUSD"], c["d_GBPUSD"])
    tr = pd.DataFrame({"time": c.index + pd.Timedelta(minutes=1), "sym": c["fautive"].to_numpy(),
                       "dir": -np.sign(dleg), "day": c["day"].to_numpy(), "move": c["move"].to_numpy()})
    tr["stop"] = [STOP_ATR * f.at[t, f"atr_{s}"] for t, s in zip(c.index, tr["sym"])]
    tr = tr[tr["dir"] != 0]
    return simulate_trades(feat, tr.reset_index(drop=True), H, early=False).dropna(subset=["r"])


def match_control(tr: pd.DataFrame, pool: pd.DataFrame, k: int = 5) -> np.ndarray:
    out = np.full(len(tr), np.nan)
    for i, row in enumerate(tr.itertuples(index=False)):
        p = pool[(pool["sym"] == row.sym) & (pool["move"] >= 0.9 * row.move) & (pool["move"] <= 1.1 * row.move)]
        if len(p):
            idx = (p["move"] - row.move).abs().nsmallest(k).index
            out[i] = p.loc[idx, "r"].mean()
    return out


def day_boot_mean(vals: np.ndarray, days, n_boot=10000, seed=11) -> list:
    s = pd.Series(vals, index=pd.Index(days)).dropna()
    if len(s) == 0:
        return [np.nan, np.nan]
    g = s.groupby(level=0)
    sums, cnts = g.sum().to_numpy(), g.count().to_numpy()
    rng = np.random.default_rng(seed)
    b = []
    for _ in range(n_boot):
        ix = rng.integers(0, len(sums), len(sums))
        b.append(sums[ix].sum() / cnts[ix].sum())
    return [float(np.quantile(b, .025)), float(np.quantile(b, .975))]
