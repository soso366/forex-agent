"""E006 — retour de la dérive asiatique (00:00-07:00 UTC) à l'ouverture de Londres. Règles : ../protocol.md.
Réutilise en LECTURE SEULE research/v4 (data._read, bars, atr, PIP ; sim.Market, simulate) et research/common/robustness.

Conventions : index UTC = début de minute. D = mid_open(minute b) - mid_open(minute a) : connu à b (open).
ATR M5(14) : barre dont la FIN est <= b (label b-5 min). Entrée : open M1 de b+5 min. Rien de postérieur à b n'entre
dans z, la direction ni le filtre ; seuls les diagnostics (sweep/ré-entrée) regardent après l'entrée.
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
MAIN_PAIRS = ("EURUSD", "GBPUSD")
STOP_ATR = 3.0
RANGE_MIN = 0.5          # range de la fenêtre < 0.5 x (range journalier moyen 20 j) x (heures/7) -> pas de trade
N_MIN = 150
COSTS = (0.0, 0.2, 0.5, 1.0)
N_PERM = 1000
WINDOWS = {   # (début h UTC, fin h UTC)
    "main": (0, 7), "pl_07_12": (7, 12), "pl_12_16": (12, 16), "pl_09_13": (9, 13), "pl_00_04": (0, 4)}
VARIANTS = {   # id: (fenêtre, zmin, hold min, spread_cond, direction, paires)
    "V1": ("main", 1.0, 240, False, +1, MAIN_PAIRS),     # RÈGLE PRINCIPALE
    "V2": ("main", 1.5, 240, False, +1, MAIN_PAIRS),
    "V3": ("main", 1.0, 120, False, +1, MAIN_PAIRS),
    "V4": ("main", 1.5, 120, False, +1, MAIN_PAIRS),
    "V5": ("main", 1.0, 240, True, +1, MAIN_PAIRS),
    "V6": ("main", 1.0, 240, False, +1, ("USDJPY",)),
}
DIAG_Z = (0.8, 1.0, 1.25, 1.5)
DIAG_HOLD = (120, 180, 240)
SPLITS = {"train": ("2025-09-01", "2026-03-01"), "validation": ("2026-03-01", "2026-09-01")}
SRC = {"train": ["m1_2025"], "validation": ["m1_2025", "m1"]}   # validation charge le train pour l'échauffement 20 j
LONDON = ZoneInfo("Europe/London")


def load(split):
    out = {}
    for s in PAIRS:
        for d in SRC[split]:
            p = ROOT / "data" / d / f"{s}.csv"
            if not p.exists():
                raise SystemExit(f"DONNÉES ABSENTES : {p}")
        out[s] = _read([ROOT / "data" / d for d in SRC[split]], s)
    return out


class Pair:
    def __init__(self, df, sym):
        self.sym, self.pip, self.df = sym, PIP[sym], df
        self.mkt = Market(df)
        self.day0 = df.index[0].floor("D")
        n = (df.index[-1].floor("D") - self.day0).days + 1
        g = pd.date_range(self.day0, periods=n * 1440, freq="1min", tz="UTC")
        x = df.reindex(g)
        self.grid = g
        self.mo = ((x["bo"] + x["ao"]) / 2).to_numpy()
        self.mh = ((x["bh"] + x["ah"]) / 2).to_numpy()
        self.ml = ((x["bl"] + x["al"]) / 2).to_numpy()
        self.sp = (x["ac"] - x["bc"]).to_numpy()
        self.ndays = n
        a = atr(bars(df, "5min"), 14)
        self.atr = {t: v for t, v in zip(a.index, a.to_numpy())}
        # range journalier (jours avec >= 1000 minutes)
        self.dr = np.full(n, np.nan)
        for k in range(n):
            h, l = self.mh[k * 1440:(k + 1) * 1440], self.ml[k * 1440:(k + 1) * 1440]
            if np.isfinite(h).sum() >= 1000:
                self.dr[k] = np.nanmax(h) - np.nanmin(l)

    def _at(self, k, minute):
        """mid_open de la minute, tolérance 2 min (première minute présente)."""
        for j in range(3):
            v = self.mo[k * 1440 + minute + j]
            if np.isfinite(v):
                return v
        return np.nan

    def events(self, name, d_from, d_to, hist_ok=None):
        """Une ligne par jour ouvré de [d_from, d_to) (UTC) : toutes les infos connues à l'heure b."""
        ha, hb = WINDOWS[name]
        a_min, b_min = ha * 60, hb * 60
        rows, spw = [], {}
        for k in range(self.ndays):
            day = self.day0 + pd.Timedelta(days=k)
            seg = self.sp[k * 1440 + a_min:k * 1440 + b_min]
            spw[k] = np.nanmean(seg) if np.isfinite(seg).sum() >= 0.5 * (b_min - a_min) else np.nan
        for k in range(self.ndays):
            day = self.day0 + pd.Timedelta(days=k)
            if day < pd.Timestamp(d_from, tz="UTC") or day >= pd.Timestamp(d_to, tz="UTC") or day.weekday() > 4:
                continue
            ta, tb = day + pd.Timedelta(minutes=a_min), day + pd.Timedelta(minutes=b_min)
            pa, pb = self._at(k, a_min), self._at(k, b_min)
            a_ = self.atr.get(tb - pd.Timedelta(minutes=5), np.nan)     # barre finie à b
            h = self.mh[k * 1440 + a_min:k * 1440 + b_min]
            l = self.ml[k * 1440 + a_min:k * 1440 + b_min]
            if not (np.isfinite(pa) and np.isfinite(pb) and np.isfinite(a_) and a_ > 0 and np.isfinite(h).any()):
                continue
            prev = [self.dr[j] for j in range(k - 1, -1, -1) if np.isfinite(self.dr[j])][:20]   # jours < k seulement
            prevsp = [spw[j] for j in range(k - 1, -1, -1) if np.isfinite(spw[j])][:20]
            if len(prev) < 10 or len(prevsp) < 10:
                continue
            nb = (b_min - a_min) / 5
            D = pb - pa
            rng = np.nanmax(h) - np.nanmin(l)
            off = (day + pd.Timedelta(hours=7)).tz_convert(LONDON).utcoffset()
            rows.append(dict(day=day.tz_localize(None).normalize(), sym=self.sym, k=k, ta=ta, tb=tb, D=D, atr=a_,
                             z=D / (a_ * np.sqrt(nb)), rng=rng, hi=np.nanmax(h), lo=np.nanmin(l),
                             filt_ok=bool(rng >= RANGE_MIN * np.mean(prev) * (hb - ha) / 7),
                             spread_hi=bool(spw[k] > np.median(prevsp)) if np.isfinite(spw[k]) else False,
                             utc1=bool(off.total_seconds() == 3600)))
        return pd.DataFrame(rows)


def select(ev, zmin, spread_cond, zmax=None):
    m = ev["filt_ok"] & (ev["z"].abs() >= zmin)
    if zmax is not None:
        m &= ev["z"].abs() < zmax
    if spread_cond:
        m &= ev["spread_hi"]
    return ev[m]


def sim_events(P: Pair, ev, hold, direction=+1):
    """direction=+1 : fade (sens opposé à D) ; -1 : continuation. Entrée open M1 de b+5 min, stop 3 ATR, sortie temps."""
    if len(ev) == 0:
        return pd.DataFrame()
    d = -np.sign(ev["D"].to_numpy()) * direction
    et = ev["tb"] + pd.Timedelta(minutes=5)
    sd = STOP_ATR * ev["atr"].to_numpy()
    s = simulate(P.mkt, et, d, sd, np.full(len(ev), np.inf), hold=hold, max_gap_min=1)
    t = pd.concat([ev.reset_index(drop=True), s], axis=1)
    t["time"] = et.reset_index(drop=True)
    t["dir"] = d
    t["stop"] = sd
    t = t[t["exit"] != "skip"].reset_index(drop=True)
    assert (t["time"] + pd.to_timedelta(t["minutes"], unit="m")).dt.hour.max() < 21
    # diagnostics (regardent après l'entrée : jamais utilisés pour décider d'un trade)
    sweep, reent = [], []
    for _, r in t.iterrows():
        i0 = r["k"] * 1440 + int(((r["time"] - (P.day0 + pd.Timedelta(days=int(r["k"])))).total_seconds()) // 60)
        i1 = i0 + int(r["minutes"])
        h, l = np.nanmax(P.mh[i0:i1]), np.nanmin(P.ml[i0:i1])
        mid = (r["hi"] + r["lo"]) / 2
        if r["D"] > 0:
            sweep.append(bool(h > r["hi"])); reent.append(bool(l <= mid))
        else:
            sweep.append(bool(l < r["lo"])); reent.append(bool(h >= mid))
    t["sweep"], t["reentry"] = sweep, reent
    return t


def day_series(t):
    """Une valeur par jour = moyenne des R des paires tradées ce jour (paires corrélées moyennées)."""
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


def perm_test(evs: dict, hold, n_perm=N_PERM, seed=7):
    """Signe de D mélangé entre jours (par paire), mêmes jours déclencheurs. evs = {sym: (P, ev sélectionnés)}."""
    rng = np.random.default_rng(seed)
    parts = []
    for sym, (P, ev) in evs.items():
        if len(ev) == 0:
            continue
        up = sim_events(P, ev.assign(D=np.abs(ev["D"])), hold, +1)       # D>0 -> vente
        dn = sim_events(P, ev.assign(D=-np.abs(ev["D"])), hold, +1)      # D<0 -> achat
        key = ["tb"]
        m = up[key + ["r"]].merge(dn[key + ["r"]], on=key, suffixes=("_s", "_b"))
        sg = np.sign(ev.set_index("tb").loc[m["tb"], "D"].to_numpy())
        parts.append((m["r_s"].to_numpy(), m["r_b"].to_numpy(), sg))
    if not parts:
        return dict(p=np.nan)
    real = np.concatenate([np.where(sg > 0, rs, rb_) for rs, rb_, sg in parts]).mean()
    sims = np.empty(n_perm)
    for i in range(n_perm):
        sims[i] = np.concatenate([np.where(rng.permutation(sg) > 0, rs, rb_) for rs, rb_, sg in parts]).mean()
    return dict(real=float(real), perm_mean=float(sims.mean()), perm_q95=float(np.quantile(sims, .95)),
                p=float((1 + (sims >= real).sum()) / (n_perm + 1)), n_perm=n_perm)


def cost_stats(t, extra):
    return rb.stats(t["r"] - extra * t["sym"].map(PIP) / t["stop"])
