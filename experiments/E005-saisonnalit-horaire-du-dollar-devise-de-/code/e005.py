"""E005 - saisonnalité horaire du dollar. Règles : ../protocol.md (verrouillé).
Réutilise en LECTURE SEULE research/v4/data.py (_read, bars, atr, PIP), research/v4/sim.py (Market, simulate),
research/common/robustness.py. R = pips / ATR M5(14) à l'entrée (UNE définition) ; stop catastrophe = 3 ATR."""
from __future__ import annotations

import sys
from datetime import datetime, time as dtime, timedelta
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
# direction par fenêtre (EURUSD, GBPUSD, USDJPY)
DIR_A = {"EURUSD": -1, "GBPUSD": -1, "USDJPY": +1}
DIR_B = {s: -d for s, d in DIR_A.items()}
# variantes figées (8) : (heure locale de début, durée min, directions)
VARIANTS = {
    "A": (8.0, 240, DIR_A), "B": (14.0, 240, DIR_B),
    "A2h": (8.0, 120, DIR_A), "B2h": (14.0, 120, DIR_B),
    "A3h": (8.0, 180, DIR_A), "B3h": (14.0, 180, DIR_B),
    # "A+B" = union des trades de A et B ; "A|Bveille" = A filtré (voir run.py)
}
SENS = {"A_m30": (7.5, 240, DIR_A), "A_p30": (8.5, 240, DIR_A), "A_3h": VARIANTS["A3h"], "A_5h": (8.0, 300, DIR_A)}
# placebo : débuts locaux ne chevauchant pas [8,12) et finissant avant 20:00 UTC, durée 240 min
PLACEBO_STARTS = [0.0, 1.0, 2.0, 3.0, 4.0, 12.0, 13.0, 14.0, 15.0, 16.0]
EXCLUDE_MD = {(12, 24), (12, 25), (12, 26), (12, 31), (1, 1)}
FOMC = {"2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
        "2026-07-29"}
WINDOWS = {
    "train": dict(dirs=["m1_2025"], start="2025-09-02", end="2026-03-01"),
    "validation": dict(dirs=["m1"], start="2026-03-02", end="2026-09-01"),
}


def local_to_utc(d, hour: float) -> pd.Timestamp:
    """Date locale Londres + heure locale -> Timestamp UTC (zoneinfo, jamais un +1h fixe)."""
    h, m = int(hour), int(round((hour - int(hour)) * 60))
    dt = datetime.combine(d, dtime(h, m), tzinfo=LON)
    return pd.Timestamp(dt).tz_convert("UTC")


def is_nfp(d) -> bool:
    return d.weekday() == 4 and d.day <= 7


def load_window(name: str) -> dict:
    w = WINDOWS[name]
    miss = [str(ROOT / "data" / d / f"{s}.csv") for d in w["dirs"] for s in PAIRS
            if not (ROOT / "data" / d / f"{s}.csv").exists()]
    if miss:
        raise SystemExit("DONNEES ABSENTES : " + ", ".join(miss))
    return {s: _read([ROOT / "data" / d for d in w["dirs"]], s) for s in PAIRS}


class Pair:
    def __init__(self, df: pd.DataFrame, sym: str):
        self.sym, self.df, self.market = sym, df, Market(df)
        a = atr(bars(df, "5min"), 14)
        a.index = a.index + pd.Timedelta(minutes=5)          # disponible à la FIN de la barre
        self.atr = a
        self.t = df.index.values


def days_of(w) -> list:
    return [d.date() for d in pd.bdate_range(w["start"], pd.Timestamp(w["end"]) - pd.Timedelta(days=1))
            if (d.month, d.day) not in EXCLUDE_MD]


def signals(pairs: dict, w: dict, start_h: float, dur: int, dirs: dict) -> pd.DataFrame:
    """Un signal par paire et par jour ouvré (liste d'exclusion écrite). Sans R."""
    rows = []
    for s, p in pairs.items():
        for d in days_of(w):
            t0 = local_to_utc(d, start_h)
            t1 = t0 + pd.Timedelta(minutes=dur)
            if t1.hour * 60 + t1.minute > 21 * 60 or t1.date() != t0.date():
                continue
            a = p.atr.asof(t0)
            i0 = np.searchsorted(p.t, np.datetime64(t0.tz_localize(None)))
            j1 = np.searchsorted(p.t, np.datetime64(t1.tz_localize(None)))
            if not (np.isfinite(a) and a > 0) or (j1 - i0) < MIN_PRESENT * dur:
                continue
            rows.append((t0, s, dirs[s], float(a), dur, d))
    return pd.DataFrame(rows, columns=["time", "sym", "dir", "atr", "hold", "day"])


def simulate_trades(pairs: dict, sig: pd.DataFrame) -> pd.DataFrame:
    """R en unité 1 ATR : r = 3 * r_sim (stop catastrophe = 3 ATR). stop = ATR (unité de R pour robustness.costs)."""
    out = []
    for s, g in sig.groupby("sym"):
        g = g.reset_index(drop=True)
        res = simulate(pairs[s].market, g["time"], g["dir"], STOP_ATR * g["atr"], np.full(len(g), np.inf),
                       hold=int(g["hold"].iloc[0]), max_gap_min=1)
        x = g.join(res)
        x["r"] = x["r"] * STOP_ATR
        x["stop"] = x["atr"]
        x["pips"] = x["r"] * x["atr"] / PIP[s]
        out.append(x)
    if not out:
        return pd.DataFrame(columns=list(sig.columns) + ["r", "stop", "pips", "exit"])
    t = pd.concat(out, ignore_index=True).dropna(subset=["r"]).sort_values(["time", "sym"]).reset_index(drop=True)
    return t


def make(pairs, w, spec):
    h, dur, dirs = spec
    return simulate_trades(pairs, signals(pairs, w, h, dur, dirs))


def day_stats(t: pd.DataFrame) -> dict:
    d = t.groupby("day")["r"].sum() if len(t) else pd.Series(dtype=float)
    n = len(d)
    sd = d.std(ddof=1) if n > 1 else np.nan
    return {"days": n, "mean_day_sum": float(d.mean()) if n else np.nan,
            "t": float(d.mean() / (sd / np.sqrt(n))) if n > 1 and sd > 0 else np.nan}


def week_boot(t: pd.DataFrame, n_boot=10000, seed=11) -> dict:
    """IC 95 % bootstrap par blocs de semaine de la somme R quotidienne -> moyenne par trade (ratio)."""
    wk = pd.to_datetime(t["day"]).dt.to_period("W")
    S = t.groupby(wk)["r"].sum()
    C = t.groupby(wk)["r"].count()
    rng = np.random.default_rng(seed)
    W = rng.multinomial(len(S), np.full(len(S), 1 / len(S)), size=n_boot).astype(float)
    e = (W @ S.to_numpy()) / (W @ C.to_numpy())
    return {"ci95": [float(np.quantile(e, .025)), float(np.quantile(e, .975))], "weeks": int(len(S))}


def day_boot_diff(true_t: pd.DataFrame, plac: list, n_boot=10000, seed=11) -> dict:
    """IC 95 % bootstrap par jour de exp(vrai) - moyenne des exp(placebos), tirage apparié des jours."""
    sets = [true_t] + plac
    days = sorted(set().union(*[set(x["day"]) for x in sets if len(x)]))
    di = {d: k for k, d in enumerate(days)}
    D, G = len(days), len(sets)
    S, C = np.zeros((D, G)), np.zeros((D, G))
    for gi, x in enumerate(sets):
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
            "days": D}


def sign_perm_p(t: pd.DataFrame, n=5000, seed=7) -> dict:
    """Placebo par jours : signe aléatoire par jour (panier) ; p = P(moyenne >= observée)."""
    d = t.groupby("day")["r"].sum().to_numpy()
    c = t.groupby("day")["r"].count().to_numpy()
    obs = d.sum() / c.sum()
    rng = np.random.default_rng(seed)
    sg = rng.choice([-1.0, 1.0], size=(n, len(d)))
    m = (sg @ d) / c.sum()
    return {"obs": float(obs), "p": float((m >= obs).mean()), "n": n}


def nets(t: pd.DataFrame, extra_pips: float) -> dict:
    r = t["r"] - extra_pips * t["sym"].map(PIP) / t["stop"]
    return rb.stats(r)


def months(t: pd.DataFrame) -> dict:
    m = pd.to_datetime(t["day"]).dt.strftime("%Y-%m")
    return {k: rb.stats(g["r"]) for k, g in t.groupby(m)}


def conc(t: pd.DataFrame) -> dict:
    ds = t.groupby("day")["r"].sum().sort_values()
    best, worst = set(ds.index[-5:]), set(ds.index[:5])
    ann = t["day"].map(lambda d: is_nfp(d) or d.isoformat() in FOMC)
    tot = t["r"].sum()
    return {"without_top5_days": rb.stats(t.loc[~t["day"].isin(best), "r"]),
            "without_worst5_days": rb.stats(t.loc[~t["day"].isin(worst), "r"]),
            "announce_days_share_of_total": float(t.loc[ann, "r"].sum() / tot) if tot else None,
            "without_announce_days": rb.stats(t.loc[~ann, "r"]), "n_announce_trades": int(ann.sum())}
