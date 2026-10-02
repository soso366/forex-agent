"""E002 — choc de spread hors heure ronde : retour après normalisation de la liquidité.

Règles : voir ../protocol.md (verrouillé). Réutilise research/v4/data.py (_read, bars, atr) et research/v4/sim.py
(Market, simulate avec max_gap_min=1) en LECTURE SEULE.

Conventions : index UTC = début de minute ; une minute t est « connue » à sa clôture (t + 1 min).
Grille minute complète : la position p ↔ minute ; p−3 = t−3 min (horodatage, pas rang d'index).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.v4.data import _read, atr, bars  # noqa: E402
from research.v4.sim import Market, simulate  # noqa: E402

TZ = "UTC"
PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
NDAYS = 20
NORM_MULT = 1.5
ATR_MOVE = 1.0
STOP_ATR = 1.5
COOLDOWN = pd.Timedelta(minutes=30)
NORM_WIN = 5
RETR_MAX = 0.5
FFILL = 2
N_MIN_PRINCIPAL = 80

# id : seuil de spread (× ref), durée H (min), cible 50 % (True/False)
VARIANTS = {
    "V1": dict(thr=3.0, H=15, tgt=True), "V2": dict(thr=3.0, H=15, tgt=False),
    "V3": dict(thr=3.0, H=30, tgt=True), "V4": dict(thr=3.0, H=30, tgt=False),
    "V5": dict(thr=2.5, H=15, tgt=True), "V6": dict(thr=2.5, H=15, tgt=False),
    "V7": dict(thr=2.5, H=30, tgt=True), "V8": dict(thr=2.5, H=30, tgt=False),
}
PRINCIPAL, FALLBACK = "V1", "V5"


def neighbors(vid: str) -> list[str]:
    v = VARIANTS[vid]
    return [k for k, w in VARIANTS.items() if k != vid and sum(v[d] != w[d] for d in ("thr", "H", "tgt")) == 1]


WINDOWS = {
    "train": dict(dirs=["m1_2025"], start="2025-09-01", end="2026-03-01"),
    "valA": dict(dirs=["m1_2025", "m1"], start="2026-03-01", end="2026-09-01"),
    "valB": dict(dirs=["m1_locked_2024", "m1_locked"], start="2024-09-01", end="2025-09-01"),
}

# Jours fériés / liquidité mince pré-déclarés (diagnostic + critère « sans fériés > 0 »)
HOLIDAYS = {pd.Timestamp(x).date() for x in [
    # Validation B
    "2024-09-02", "2024-10-14", "2024-11-11", "2024-11-28", "2024-11-29", "2024-12-24", "2024-12-25", "2024-12-26",
    "2024-12-31", "2025-01-01", "2025-01-02", "2025-01-20", "2025-02-17", "2025-04-18", "2025-04-21", "2025-05-05",
    "2025-05-26", "2025-06-19", "2025-07-04", "2025-08-25",
    # Train
    "2025-09-01", "2025-10-13", "2025-11-11", "2025-11-27", "2025-11-28", "2025-12-24", "2025-12-25", "2025-12-26",
    "2025-12-31", "2026-01-01", "2026-01-02", "2026-01-19", "2026-02-16",
    # Validation A
    "2026-04-03", "2026-04-06", "2026-05-04", "2026-05-25", "2026-06-19", "2026-07-03", "2026-08-31"]}


def load_window(name: str) -> dict:
    w = WINDOWS[name]
    return {s: _read([ROOT / "data" / d for d in w["dirs"]], s) for s in PAIRS}


# ----------------------------------------------------------------------------------------------- features
class PairFeatures:
    """Toutes les colonnes à la position p n'utilisent que des minutes ≤ p (ref : jours < jour courant ;
    ATR : M5 dont la fin ≤ clôture de p)."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        g = pd.date_range(df.index[0].floor("D"), df.index[-1].ceil("D"), freq="1min", tz="UTC", inclusive="left")
        self.grid = g
        x = df.reindex(g)
        self.ex = x["bc"].notna().to_numpy()
        self.bo, self.bh, self.bl, self.bc = (x[c].to_numpy() for c in ("bo", "bh", "bl", "bc"))
        self.ao, self.ah, self.al, self.ac = (x[c].to_numpy() for c in ("ao", "ah", "al", "ac"))
        self.s = np.fmax(self.ao - self.bo, self.ac - self.bc)
        self.s[~self.ex] = np.nan
        self.mc = (self.bc + self.ac) / 2
        self.mh = (self.bh + self.ah) / 2
        self.ml = (self.bl + self.al) / 2
        ff = lambda a: pd.Series(a).ffill(limit=FFILL).to_numpy()  # noqa: E731
        self.mc_ff, self.bc_ff, self.ac_ff = ff(self.mc), ff(self.bc), ff(self.ac)
        # ATR M5 (mid), disponible à la FIN de la barre : étiquette + 5 min ; lu à la clôture de p (= p + 1 min)
        b = bars(df, "5min")
        a = atr(b, 14)
        a.index = a.index + pd.Timedelta(minutes=5)
        self.atr = a.reindex(g + pd.Timedelta(minutes=1), method="ffill").to_numpy()
        # référence de spread : médiane, même créneau 30 min UTC, 20 jours ouvrés précédents (jour courant exclu)
        self.ref = self._ref()
        self.hm = (g.hour * 60 + g.minute).to_numpy()
        self.wd = g.weekday.to_numpy()
        self.mm = g.minute.to_numpy()
        self.day = g.normalize().tz_localize(None).date

    def _ref(self) -> np.ndarray:
        g = self.grid
        n = len(g)
        nd = n // 1440
        S = self.s[: nd * 1440].reshape(nd, 48, 30)
        days = g[::1440][:nd]
        wd = days.weekday.to_numpy()
        has = np.isfinite(S).any(axis=(1, 2))
        bd = np.nonzero((wd < 5) & has)[0]          # jours ouvrés avec cotations
        ref = np.full((nd, 48), np.nan)
        for k, i in enumerate(bd):
            if k < NDAYS:
                continue
            prev = bd[k - NDAYS:k]
            with np.errstate(all="ignore"):
                blk = S[prev].transpose(1, 0, 2).reshape(48, -1)
                ok = np.isfinite(blk).any(axis=1)
                r = np.full(48, np.nan)
                r[ok] = np.nanmedian(blk[ok], axis=1)
            ref[i] = r
        out = np.repeat(ref.reshape(nd, 48), 30, axis=1).reshape(-1)
        return np.concatenate([out, np.full(n - len(out), np.nan)])

    def delta(self, mode: str):
        """Δ entre la clôture de t−3 et la clôture de t. mid | A1 (ask si hausse, bid si baisse) | A2 (les deux côtés)."""
        L = 3
        sh = lambda a: np.concatenate([np.full(L, np.nan), a[:-L]])  # noqa: E731
        dm = self.mc - sh(self.mc_ff)
        if mode == "mid":
            return dm
        db, da = self.bc - sh(self.bc_ff), self.ac - sh(self.ac_ff)
        if mode == "A1":
            d = np.where(dm > 0, da, db)
            return np.where(np.sign(d) == np.sign(dm), d, 0.0)
        if mode == "A2":
            same = (np.sign(db) == np.sign(dm)) & (np.sign(da) == np.sign(dm))
            return np.where(same, np.sign(dm) * np.minimum(np.abs(db), np.abs(da)), 0.0)
        raise ValueError(mode)


def hours_ok(f: PairFeatures) -> np.ndarray:
    hm = f.hm
    ok = (hm >= 6 * 60) & (hm < 20 * 60) & (f.wd < 5)
    ok &= ~((hm >= 20 * 60 + 30) & (hm < 22 * 60 + 30))
    ok &= ~((f.wd == 0) & (hm < 7 * 60))
    return ok


def round_minute(f: PairFeatures) -> np.ndarray:
    r = f.mm % 15
    return np.minimum(r, 15 - r) <= 2


def candidates(f: PairFeatures, sym: str, thr: float, spread: str = "shock", rnd: bool = False,
               dmode: str = "mid", start=None, end=None) -> pd.DataFrame:
    """Signaux (avant cooldown) : minute de choc t, normalisation m ≤ t+5, entrée à l'ouverture de m+1."""
    d = f.delta(dmode)
    base = f.ex & np.isfinite(f.ref) & np.isfinite(f.atr) & (f.atr > 0) & hours_ok(f)
    base &= round_minute(f) if rnd else ~round_minute(f)
    base &= np.abs(d) >= ATR_MOVE * f.atr
    if spread == "shock":
        base &= f.s >= thr * f.ref
    else:                               # contrôle « même mouvement, spread normal »
        base &= f.s < NORM_MULT * f.ref
    g = f.grid
    if start is not None:
        base &= (g >= pd.Timestamp(start, tz="UTC")) & (g < pd.Timestamp(end, tz="UTC"))
    idx = np.nonzero(base)[0]
    N = len(g)
    rows = []
    for p in idx:
        m = -1
        for j in range(1, NORM_WIN + 1):
            q = p + j
            if q < N and f.ex[q] and np.isfinite(f.ref[q]) and f.s[q] <= NORM_MULT * f.ref[q]:
                m = q
                break
        if m < 0:
            continue
        e = m + 1
        if e >= N or not f.ex[e]:
            continue
        sg = np.sign(d[p])
        ad = abs(d[p])
        lo = max(p - 2, 0)
        X = np.nanmax(f.mh[lo:m + 1]) if sg > 0 else np.nanmin(f.ml[lo:m + 1])
        retr = sg * (X - f.mc[m]) / ad
        if retr > RETR_MAX:
            continue
        L = X - sg * 0.5 * ad
        dr = -sg
        px = f.ao[e] if dr > 0 else f.bo[e]
        td = dr * (L - px)
        if not td > 0:
            continue                    # le prix d'entrée a déjà dépassé le niveau de retour 50 %
        rows.append((g[e], g[p], sym, int(dr), ad, ad / f.atr[p], STOP_ATR * f.atr[p], td, m - p,
                     float(f.s[p] / f.ref[p]), _isolated(f, p, d, thr)))
    cols = ["time", "shock_time", "sym", "dir", "move", "move_atr", "stop", "tdist", "norm_lag", "spread_x", "isolated"]
    return pd.DataFrame(rows, columns=cols)


def _isolated(f: PairFeatures, p: int, d, thr) -> bool:
    """Contrôle données : écart de spread sur la seule minute t (voisines normales) et mouvement entièrement dans t."""
    if p < 3 or p + 1 >= len(f.s):
        return False
    nb = all(np.isfinite(f.s[q]) and np.isfinite(f.ref[q]) and f.s[q] < NORM_MULT * f.ref[q] for q in (p - 1, p + 1))
    pre = f.mc_ff[p - 1] - f.mc_ff[p - 3]
    return bool(nb and np.isfinite(pre) and abs(pre) < 0.25 * abs(d[p]))


def cooldown(c: pd.DataFrame) -> pd.DataFrame:
    """Un trade par paire par épisode ; pas de nouvelle entrée < 30 min après l'entrée précédente sur la paire."""
    if c.empty:
        return c
    keep = []
    for s, g in c.sort_values("shock_time").groupby("sym", sort=False):
        last = None
        for i, r in g.iterrows():
            if last is None or r["time"] >= last + COOLDOWN:
                keep.append(i)
                last = r["time"]
    return c.loc[keep].sort_values("time").reset_index(drop=True)


def signals(feats: dict, thr, start, end, **kw) -> pd.DataFrame:
    parts = [candidates(feats[s], s, thr, start=start, end=end, **kw) for s in PAIRS]
    parts = [p for p in parts if len(p)]
    if not parts:
        return pd.DataFrame(columns=["time", "shock_time", "sym", "dir", "move", "move_atr", "stop", "tdist",
                                     "norm_lag", "spread_x", "isolated"])
    return cooldown(pd.concat(parts, ignore_index=True))


def run_trades(feats: dict, tr: pd.DataFrame, H: int, tgt: bool) -> pd.DataFrame:
    out = []
    for s, g in tr.groupby("sym"):
        mk = Market(feats[s].df)
        r = simulate(mk, g["time"], g["dir"], g["stop"], g["tdist"] if tgt else np.full(len(g), np.inf),
                     hold=H, max_gap_min=1)
        out.append(g.reset_index(drop=True).join(r))
    if not out:
        return tr.assign(r=[], exit=[])
    t = pd.concat(out, ignore_index=True).dropna(subset=["r"]).sort_values("time").reset_index(drop=True)
    t["day"] = pd.DatetimeIndex(t["time"]).normalize().tz_localize(None).date
    return t


def episodes(t: pd.DataFrame) -> np.ndarray:
    """Chocs simultanés (entrées à ±2 min, toutes paires) = un épisode."""
    tt = pd.DatetimeIndex(t["time"]).as_unit("ns").asi8
    o = np.argsort(tt)
    ep = np.zeros(len(t), int)
    k, prev = 0, None
    for i in o:
        if prev is not None and tt[i] - prev > 2 * 60 * 10 ** 9:
            k += 1
        ep[i] = k
        prev = tt[i]
    return ep


def day_boot_diff(a: pd.DataFrame, b: pd.DataFrame, n_boot=10000, seed=11) -> list:
    """IC 95 % de (moyenne/trade de a − moyenne/trade de b), bootstrap par jours, indépendant pour chaque échantillon."""
    if len(a) == 0 or len(b) == 0:
        return [np.nan, np.nan]
    ga, gb = a.groupby("day")["r"], b.groupby("day")["r"]
    sa, ca, sb, cb = ga.sum().to_numpy(), ga.count().to_numpy(), gb.sum().to_numpy(), gb.count().to_numpy()
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for k in range(n_boot):
        i = rng.integers(0, len(sa), len(sa))
        j = rng.integers(0, len(sb), len(sb))
        out[k] = sa[i].sum() / ca[i].sum() - sb[j].sum() / cb[j].sum()
    return [float(np.quantile(out, .025)), float(np.quantile(out, .975))]


def placebo(feats: dict, tr: pd.DataFrame, H: int, tgt: bool, n_draws=200, seed=5) -> dict:
    """Entrée à une minute tirée au hasard dans la même heure UTC du même jour, sens opposé au mouvement mid des
    3 dernières minutes, même stop (1,5 ATR M5 à cette minute), même sortie. Graine fixe."""
    rng = np.random.default_rng(seed)
    pos = {}
    for s in PAIRS:
        f = feats[s]
        pos[s] = pd.Series(np.arange(len(f.grid)), index=f.grid)
    means = []
    for _ in range(n_draws):
        rows = []
        for _, r in tr.iterrows():
            f = feats[r["sym"]]
            h0 = r["time"].floor("h")
            p0 = pos[r["sym"]][h0]
            u = p0 + int(rng.integers(0, 60))
            e = u + 1
            if e >= len(f.grid) or not (f.ex[u] and f.ex[e]) or not np.isfinite(f.atr[u]):
                continue
            d3 = f.mc[u] - f.mc_ff[u - 3]
            if not np.isfinite(d3) or d3 == 0:
                continue
            sg = np.sign(d3)
            X = np.nanmax(f.mh[u - 2:u + 1]) if sg > 0 else np.nanmin(f.ml[u - 2:u + 1])
            dr = -sg
            px = f.ao[e] if dr > 0 else f.bo[e]
            td = dr * ((X - sg * 0.5 * abs(d3)) - px)
            rows.append((f.grid[e], r["sym"], dr, STOP_ATR * f.atr[u], td if (tgt and td > 0) else np.inf))
        if not rows:
            continue
        p = pd.DataFrame(rows, columns=["time", "sym", "dir", "stop", "tdist"])
        rr = []
        for s, g in p.groupby("sym"):
            rr.append(simulate(Market(feats[s].df), g["time"], g["dir"], g["stop"], g["tdist"], hold=H,
                               max_gap_min=1)["r"])
        means.append(float(pd.concat(rr).mean()))
    m = np.array(means)
    return {"draws": int(len(m)), "p95": float(np.nanquantile(m, .95)), "mean": float(np.nanmean(m))}
