"""Données de recherche V4 : M1 bid/ask Dukascopy, toutes périodes disponibles, une table par paire.

Colonnes : bo bh bl bc (bid), ao ah al ac (ask), mid (clôture moyenne), spread (en prix).
Index : temps UTC (début de la minute). Les minutes sans cotation sont absentes (pas de remplissage).
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [ROOT / "data" / "m1_2025", ROOT / "data" / "m1"]           # sept. 2025 → fév. 2026, mars → août 2026
LOCKED = [ROOT / "data" / "m1_locked_2024", ROOT / "data" / "m1_locked"]  # sept. 2024 → août 2025 : test final uniquement
CACHE = ROOT / "research" / "v4" / "cache"
PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}
COLS = {"bid_open": "bo", "bid_high": "bh", "bid_low": "bl", "bid_close": "bc",
        "ask_open": "ao", "ask_high": "ah", "ask_low": "al", "ask_close": "ac"}


def _read(dirs, sym):
    parts = []
    for d in dirs:
        p = d / f"{sym}.csv"
        if p.exists():
            df = pd.read_csv(p, parse_dates=["time"]).rename(columns=COLS).set_index("time")
            parts.append(df)
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated()]
    df.index = df.index.tz_convert("UTC") if df.index.tz is not None else df.index.tz_localize("UTC")
    df["mid"] = (df["bc"] + df["ac"]) / 2
    df["spread"] = df["ac"] - df["bc"]
    return df.astype("float64")


def load(sym: str, locked: bool = False) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    tag = "locked" if locked else "research"
    p = CACHE / f"{sym}_{tag}.pkl"
    if p.exists():
        return pickle.load(open(p, "rb"))
    df = _read(LOCKED if locked else SOURCES, sym)
    pickle.dump(df, open(p, "wb"))
    return df


def bars(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Barres agrégées sur le mid (OHLC) + spread moyen ; label = début de barre."""
    m = (df["bo"] + df["ao"]) / 2, (df["bh"] + df["ah"]) / 2, (df["bl"] + df["al"]) / 2, df["mid"]
    x = pd.DataFrame({"o": m[0], "h": m[1], "l": m[2], "c": m[3], "spread": df["spread"]})
    g = x.resample(rule, label="left", closed="left")
    out = pd.DataFrame({"o": g["o"].first(), "h": g["h"].max(), "l": g["l"].min(), "c": g["c"].last(),
                        "spread": g["spread"].mean(), "n": g["c"].count()})
    return out[out["n"] > 0]


def atr(b: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = b["c"].shift()
    tr = np.maximum(b["h"] - b["l"], np.maximum((b["h"] - pc).abs(), (b["l"] - pc).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean()
