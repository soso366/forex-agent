"""Ajoute les volumes Dukascopy (bid_volume, ask_volume) aux CSV M1 déjà préparés par `forex_agent data-download`.

Demandé par les agents de recherche (cycles 8 à 22) et validé par l'utilisateur le 22/10/2026.
Ne modifie ni la baseline ni le format lu par CSVProvider : deux colonnes en plus, ignorées par le rejeu V2.
Les volumes viennent des mêmes fichiers bi5 déjà en cache (aucun nouveau téléchargement).
Usage : python -m forex_agent.lab.volume --start 2020-09-01 --end 2021-02-28 [--symbols EURUSD ...]
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ..data import dukascopy

ROOT = Path(__file__).resolve().parents[2]


def volumes(symbol: str, start: date, end: date, cache_dir: Path) -> pd.DataFrame:
    parts = {"BID": [], "ASK": []}
    d = start
    while d <= end:
        for side in dukascopy.SIDES:
            p = dukascopy.cache_path(cache_dir, symbol, d, side)
            if p.exists() and p.stat().st_size:
                parts[side].append(dukascopy.decode_bi5(p.read_bytes(), d, symbol)["vol"])
        d += timedelta(days=1)
    cols = {}
    for side, name in (("BID", "bid_volume"), ("ASK", "ask_volume")):
        s = pd.concat(parts[side]) if parts[side] else pd.Series(dtype=float)
        cols[name] = s[~s.index.duplicated(keep="first")]
    return pd.DataFrame(cols)


def add_volume(csv_dir: Path, symbols: list[str], start: date, end: date, cache_dir: Path) -> dict:
    rep = {}
    for s in symbols:
        path = csv_dir / f"{s}.csv"
        df = pd.read_csv(path)
        idx = pd.to_datetime(df["time"], utc=True)
        v = volumes(s, start, end, cache_dir).reindex(idx)
        df["bid_volume"] = v["bid_volume"].round(2).to_numpy()
        df["ask_volume"] = v["ask_volume"].round(2).to_numpy()
        missing = int(df["bid_volume"].isna().sum())
        df.to_csv(path, index=False)
        rep[s] = {"lignes": int(len(df)), "volumes_manquants": missing}
        print(f"  {s} : volumes ajoutés ({len(df):,} lignes, {missing} sans volume)")
    return rep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--symbols", nargs="+", default=["EURUSD", "GBPUSD", "USDJPY"])
    ap.add_argument("--csv-dir", default=str(ROOT / "data" / "m1"))
    ap.add_argument("--cache-dir", default=str(ROOT / "data" / "dukascopy_raw"))
    a = ap.parse_args()
    add_volume(Path(a.csv_dir), a.symbols, date.fromisoformat(a.start), date.fromisoformat(a.end), Path(a.cache_dir))


if __name__ == "__main__":
    main()
