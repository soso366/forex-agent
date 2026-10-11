"""E003 — nombres ronds : retournement au premier contact (ordres take-profit groupés).

Règles : voir ../protocol.md (verrouillé). Réutilise en LECTURE SEULE research/v4/data.py (_read, bars, atr, PIP),
research/v4/sim.py (Market, simulate avec max_gap_min=1), research/common/robustness.py et
forex_agent/meta/exposure.py (legs, pour la version « règles live »).

Conventions : index UTC = début de minute ; la minute t est connue à sa clôture (t + 1 min).
Grille minute complète (minutes absentes = NaN) : la position p <-> minute ; p-15, fenêtre de 120 positions =
temps d'HORLOGE, jamais des rangs de lignes présentes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from research.v4.data import PIP, _read, atr, bars  # noqa: E402
from research.v4.sim import Market, simulate  # noqa: E402
from research.common import robustness as rb  # noqa: E402

TZ = "UTC"
PAIRS = ("EURUSD", "GBPUSD", "USDJPY")

# ------------------------------------------------------------------ paramètres figés (protocol.md)
SPACING = 50            # pips entre niveaux (00 et 50)
TOL = 0.5               # tolérance de contact, pips
WIN = 120               # fenêtre « premier contact », minutes d'horloge
WIN_PRESENT = 0.75      # part minimale de minutes présentes dans la fenêtre (qualité de données)
ARR_LAG = 15            # arrivée : mid à la clôture de t-15
ARR_ATR = 0.75          # ... au moins 0,75 ATR de l'autre côté
CROSS_ATR = 0.3         # non franchi : mid high_t < L + 0,3 ATR (vente)
FFILL = 2               # t-15 / t+5 : dernière minute présente au plus 2 min avant
T_FIRST, T_LAST, T_FORCE = 7 * 60, 19 * 60 + 30, 20 * 60
SPREAD_CONTACT_PIPS = 1.0
N_MIN = 80

VARIANTS = {   # règle principale = A ; B à F = diagnostics rapportés, jamais sélectionnés
    "A": dict(spacing=50, H=20, stop=1.0, tgt=1.0),
    "B": dict(spacing=100, H=20, stop=1.0, tgt=1.0),
    "C": dict(spacing=50, H=10, stop=1.0, tgt=1.0),
    "D": dict(spacing=50, H=30, stop=1.0, tgt=1.0),
    "E": dict(spacing=50, H=20, stop=1.0, tgt=None),
    "F": dict(spacing=50, H=20, stop=0.75, tgt=1.0),
}
SENSITIVITY = {   # voisins de A (exigence 12), jamais sélectionnés
    "tol_m0.5": dict(tol=-0.5), "tol_1.5": dict(tol=1.5),
    "win60": dict(win=60), "win240": dict(win=240),
    "arr0.5": dict(arr=0.5), "arr1.0": dict(arr=1.0),
}
PLACEBO_OFFSETS = [o for o in range(6, 45) if not (20 <= o <= 30)]   # 28 grilles : 6..19 et 31..44 pips
PLACEBO_NAMED = (17, 33)

WINDOWS = {
    "train": dict(dirs=["m1_2025"], start="2025-09-02", end="2026-03-01"),
    "validation": dict(dirs=["m1_2025", "m1"], start="2026-03-01", end="2026-09-01"),
    "oos": dict(dirs=["m1_oos2324_a", "m1_oos2324_b"], start="2023-09-04", end="2024-09-01"),
}

SIG_COLS = ["time", "contact_time", "sym", "dir", "L", "offset", "level00", "atr", "atr_pips", "stop", "target",
            "hold", "spread_contact"]


class DataMissing(SystemExit):
    pass


def load_window(name: str) -> dict:
    """Charge les CSV M1 de la fenêtre ; message clair si absents (aucun téléchargement ici)."""
    w = WINDOWS[name]
    missing = [str(ROOT / "data" / d / f"{s}.csv") for d in w["dirs"] for s in PAIRS
               if not (ROOT / "data" / d / f"{s}.csv").exists()]
    if missing:
        raise DataMissing(
            "DONNÉES ABSENTES pour la fenêtre « %s » : %s\n"
            "Rien n'a été calculé. Récupérer les données avec `bash orchestrator/bootstrap.sh` "
            "(nécessite le secret DATA_REPO_TOKEN, lecture du dépôt privé forex-data)." % (name, ", ".join(missing)))
    return {s: _read([ROOT / "data" / d for d in w["dirs"]], s) for s in PAIRS}


# ------------------------------------------------------------------ niveaux
def level_above(x_price, pip, offset, spacing):
    """Plus petit niveau de la grille (k*spacing + offset pips) STRICTEMENT au-dessus de x."""
    k = np.floor((np.asarray(x_price) / pip - offset) / spacing + 1e-7) + 1
    return (k * spacing + offset) * pip


def level_below(x_price, pip, offset, spacing):
    """Plus grand niveau de la grille STRICTEMENT au-dessous de x."""
    k = np.ceil((np.asarray(x_price) / pip - offset) / spacing - 1e-7) - 1
    return (k * spacing + offset) * pip


# ------------------------------------------------------------------ données d'une paire
class PairData:
    """Toutes les colonnes à la position p n'utilisent que des minutes <= p ; l'ATR n'utilise que des barres M5
    dont la FIN est <= début de la minute p (donc entièrement avant t)."""

    def __init__(self, df: pd.DataFrame, sym: str):
        self.sym, self.pip, self.df = sym, PIP[sym], df
        g = pd.date_range(df.index[0].floor("D"), df.index[-1].floor("D") + pd.Timedelta(days=1), freq="1min",
                          tz="UTC", inclusive="left")
        self.grid = g
        x = df.reindex(g)
        self.ex = x["bc"].notna().to_numpy()
        self.bo, self.bh, self.bl, self.bc = (x[c].to_numpy() for c in ("bo", "bh", "bl", "bc"))
        self.ao, self.ah, self.al, self.ac = (x[c].to_numpy() for c in ("ao", "ah", "al", "ac"))
        self.mc = (self.bc + self.ac) / 2
        self.mh = (self.bh + self.ah) / 2
        self.ml = (self.bl + self.al) / 2
        self.mc_ff = pd.Series(self.mc).ffill(limit=FFILL).to_numpy()
        b = bars(df, "5min")
        a = atr(b, 14)
        a.index = a.index + pd.Timedelta(minutes=5)          # disponible à la FIN de la barre
        self.atr = a.reindex(g, method="ffill").to_numpy()   # à t : dernière barre finie au plus tard à t (début)
        self.hm = (g.hour * 60 + g.minute).to_numpy()
        self.wd = g.weekday.to_numpy()
        self.market = Market(df)
        self._ext = {}

    def prev_extremes(self, win: int):
        """max(ask high) et min(bid low) sur [t-win, t-1] en temps d'horloge (NaN si < 75 % de minutes présentes)."""
        if win not in self._ext:
            mp = int(np.ceil(WIN_PRESENT * win))
            pmax = pd.Series(self.ah).rolling(win, min_periods=mp).max().shift(1).to_numpy()
            pmin = pd.Series(self.bl).rolling(win, min_periods=mp).min().shift(1).to_numpy()
            self._ext[win] = (pmax, pmin)
        return self._ext[win]

    def shifted(self, a, lag):
        """a décalé de `lag` minutes d'horloge (lag > 0 : passé)."""
        out = np.full_like(a, np.nan)
        if lag > 0:
            out[lag:] = a[:-lag]
        else:
            out[:lag] = a[-lag:]
        return out


def candidates(pdat: PairData, offset=0, spacing=SPACING, tol=TOL, win=WIN, arr=ARR_ATR, H=20,
               stop_mult=1.0, tgt_r=1.0, start=None, end=None, cascade=False) -> pd.DataFrame:
    """Contacts éligibles (avant la règle « une position par paire / un trade par niveau et par jour »).
    cascade=True : renvoie au contraire les FRANCHISSEMENTS nets (diagnostic, jamais une règle)."""
    f, p = pdat, pdat.pip
    pmax, pmin = f.prev_extremes(win)
    Ls = level_above(pmax + tol * p, p, offset, spacing)          # niveau au-dessus jamais approché (fenêtre)
    Lb = level_below(pmin - tol * p, p, offset, spacing)          # niveau au-dessous jamais approché
    with np.errstate(invalid="ignore"):
        cs = f.ah >= Ls - tol * p
        cb = f.bl <= Lb + tol * p
        a = f.atr
        m15 = f.shifted(f.mc_ff, ARR_LAG)
        arr_s = m15 <= Ls - arr * a
        arr_b = m15 >= Lb + arr * a
        if not cascade:
            ok_s = cs & ~cb & arr_s & (f.mc < Ls) & (f.mh < Ls + CROSS_ATR * a)
            ok_b = cb & ~cs & arr_b & (f.mc > Lb) & (f.ml > Lb - CROSS_ATR * a)
        else:
            ok_s = cs & ~cb & arr_s & (f.mc >= Ls + CROSS_ATR * a)
            ok_b = cb & ~cs & arr_b & (f.mc <= Lb - CROSS_ATR * a)
        nxt = np.zeros_like(f.ex)
        nxt[:-1] = f.ex[1:]                                        # minute t+1 présente (entrée à son ouverture)
        base = f.ex & nxt & np.isfinite(a) & (a > 0) & np.isfinite(pmax) & np.isfinite(pmin)
        base &= (f.hm >= T_FIRST) & (f.hm <= T_LAST) & (f.wd < 5)
    g = f.grid
    if start is not None:
        base &= np.asarray((g >= pd.Timestamp(start, tz="UTC")) & (g < pd.Timestamp(end, tz="UTC")))
    rows = []
    for side, ok, L in ((-1, ok_s, Ls), (+1, ok_b, Lb)):
        idx = np.nonzero(base & ok)[0]
        for t in idx:
            lv = float(L[t])
            stop = stop_mult * a[t]
            hold = int(min(H, T_FORCE - f.hm[t + 1]))
            if side < 0:
                sc = bool(f.mh[t] < lv - SPREAD_CONTACT_PIPS * p)
            else:
                sc = bool(f.ml[t] > lv + SPREAD_CONTACT_PIPS * p)
            rows.append((g[t + 1], g[t], f.sym, side, lv, offset,
                         bool(int(round(lv / p - offset)) % 100 == 0), float(a[t]), float(a[t] / p), float(stop),
                         float(tgt_r * stop) if tgt_r is not None else np.inf, hold, sc))
    out = pd.DataFrame(rows, columns=SIG_COLS)
    if cascade and len(out):
        # mouvement mid des 5 minutes suivantes, signé dans le sens du franchissement, en ATR
        pos = g.get_indexer(pd.DatetimeIndex(out["contact_time"]))
        m5 = f.shifted(f.mc_ff, -5)
        sgn = -out["dir"].to_numpy()     # dir = sens du retournement ; le franchissement va en sens inverse
        out["move5_atr"] = sgn * (m5[pos] - f.mc[pos]) / f.atr[pos]
    return out.sort_values("contact_time").reset_index(drop=True)


def select(c: pd.DataFrame) -> pd.DataFrame:
    """Une position par paire (bloquée jusqu'à entrée + durée prévue) ; un trade par paire, niveau et jour.
    Indépendant des résultats (applicable AVANT tout calcul de R)."""
    if c.empty:
        return c
    keep = []
    for s, g in c.groupby("sym", sort=False):
        until, seen = None, set()
        for i, r in g.sort_values("contact_time").iterrows():
            key = (r["contact_time"].date(), round(r["L"], 6))
            if until is not None and r["time"] < until:
                continue
            if key in seen:
                continue
            keep.append(i)
            seen.add(key)
            until = r["time"] + pd.Timedelta(minutes=int(r["hold"]))
    return c.loc[keep].sort_values("time").reset_index(drop=True)


def signals(pdata: dict, w: dict, spacing=SPACING, offset=0, H=20, stop=1.0, tgt=1.0, tol=TOL, win=WIN,
            arr=ARR_ATR) -> pd.DataFrame:
    parts = [candidates(pdata[s], offset=offset, spacing=spacing, tol=tol, win=win, arr=arr, H=H, stop_mult=stop,
                        tgt_r=tgt, start=w["start"], end=w["end"]) for s in pdata]
    parts = [x for x in parts if len(x)]
    if not parts:
        return pd.DataFrame(columns=SIG_COLS)
    return select(pd.concat(parts, ignore_index=True))


def simulate_trades(pdata: dict, sig: pd.DataFrame) -> pd.DataFrame:
    """sim.simulate (max_gap_min=1) + stress « sortie par stop au pire prix de la minute du stop »."""
    if sig.empty:
        return sig.assign(r=[], r_stress=[], exit=[], minutes=[], exit_time=[])
    out = []
    for s, g in sig.groupby("sym"):
        m = pdata[s].market
        for h, gg in g.groupby("hold"):
            gg = gg.reset_index(drop=True)
            res = simulate(m, gg["time"], gg["dir"], gg["stop"], gg["target"], hold=int(h), max_gap_min=1)
            x = gg.join(res)
            i = m.idx(pd.DatetimeIndex(x["time"]).tz_convert("UTC").tz_localize(None))
            rs = x["r"].to_numpy().copy()
            et = np.full(len(x), np.datetime64("NaT"), dtype="datetime64[ns]")
            for k in range(len(x)):
                if not np.isfinite(x.at[k, "r"]):
                    continue
                j = i[k] + int(x.at[k, "minutes"]) - 1
                et[k] = m.t[j] + np.timedelta64(1, "m")
                if x.at[k, "exit"] == "stop":
                    d = x.at[k, "dir"]
                    px = m.ao[i[k]] if d > 0 else m.bo[i[k]]
                    worst = m.bl[j] if d > 0 else m.ah[j]
                    rs[k] = min(rs[k], d * (worst - px) / x.at[k, "stop"])
            x["r_stress"] = rs
            x["exit_time"] = pd.DatetimeIndex(et).tz_localize("UTC")
            out.append(x)
    t = pd.concat(out, ignore_index=True).dropna(subset=["r"]).sort_values("time").reset_index(drop=True)
    t["day"] = pd.DatetimeIndex(t["time"]).normalize()
    return t


# ------------------------------------------------------------------ mesures
def day_t(t: pd.DataFrame, col="r") -> dict:
    d = t.groupby("day")[col].sum() if len(t) else pd.Series(dtype=float)
    n = len(d)
    sd = d.std(ddof=1) if n > 1 else np.nan
    return {"days": n, "mean": float(d.mean()) if n else np.nan,
            "t": float(d.mean() / (sd / np.sqrt(n))) if n > 1 and sd > 0 else np.nan}


def live_rules(t: pd.DataFrame) -> pd.DataFrame:
    """Version exécutable : max 2 positions ouvertes, pas deux positions avec la même devise dans le même sens."""
    from forex_agent.meta.exposure import legs
    keep, open_ = [], []
    for i, r in t.sort_values("time").iterrows():
        open_ = [o for o in open_ if o[0] > r["time"]]
        lg = legs(r["sym"], "BUY" if r["dir"] > 0 else "SELL", 1.0)
        if len(open_) >= 2:
            continue
        if any(np.sign(o[1].get(c, 0)) == np.sign(v) and o[1].get(c, 0) != 0 for o in open_ for c, v in lg.items()):
            continue
        keep.append(i)
        open_.append((r["exit_time"], lg))
    return t.loc[keep]


def day_boot_diff(trade_sets: list, n_boot=10000, seed=11) -> dict:
    """IC 95 % bootstrap par JOUR (tirage apparié des jours) de exp(grille 0) - moyenne des exp(grilles placebo)."""
    days = sorted(set().union(*[set(x["day"]) for x in trade_sets if len(x)]))
    if not days or len(trade_sets[0]) == 0:
        return {"diff": np.nan, "ci95": [np.nan, np.nan], "days": len(days)}
    di = {d: k for k, d in enumerate(days)}
    D, G = len(days), len(trade_sets)
    S, C = np.zeros((D, G)), np.zeros((D, G))
    for gi, x in enumerate(trade_sets):
        if len(x):
            k = x["day"].map(di).to_numpy()
            np.add.at(S[:, gi], k, x["r"].to_numpy())
            np.add.at(C[:, gi], k, 1)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(D, np.full(D, 1 / D), size=n_boot).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        E = (W @ S) / (W @ C)
        diff = E[:, 0] - np.nanmean(E[:, 1:], axis=1)
        point = S[:, 0].sum() / C[:, 0].sum() - np.nanmean(S[:, 1:].sum(0) / C[:, 1:].sum(0))
    diff = diff[np.isfinite(diff)]
    return {"diff": float(point), "ci95": [float(np.quantile(diff, .025)), float(np.quantile(diff, .975))],
            "days": D, "n_boot": n_boot, "seed": seed}


def percentile_rank(x, dist) -> float:
    dist = np.asarray([d for d in dist if np.isfinite(d)])
    return float((dist < x).mean() * 100) if len(dist) else np.nan
