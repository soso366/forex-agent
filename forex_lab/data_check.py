"""Contrôle d'intégrité des données M1 Dukascopy bid/ask (sans rien corriger).

Usage : python -m forex_lab.data_check --data <dossier> [--periods 2024sep-2025feb ...]
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .engine import PERIODS, pip

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY"]


def check(df: pd.DataFrame, symbol: str) -> dict:
    p = pip(symbol)
    t = pd.to_datetime(df["time"], utc=True)
    r = {"lignes": int(len(df)), "debut": str(t.iloc[0]), "fin": str(t.iloc[-1]),
         "doublons_horodatage": int(t.duplicated().sum()), "ordre_chronologique": bool(t.is_monotonic_increasing)}
    for side in ("bid", "ask"):
        o, h, l, c = (df[f"{side}_{k}"] for k in ("open", "high", "low", "close"))
        r[f"ohlc_incoherent_{side}"] = int(((h < np.maximum(o, c)) | (l > np.minimum(o, c))).sum())
        r[f"prix_nuls_ou_negatifs_{side}"] = int(((o <= 0) | (h <= 0) | (l <= 0) | (c <= 0)).sum())
    spread = (df["ask_close"] - df["bid_close"]) / p
    r["ask_sous_bid"] = int((spread < 0).sum())
    r["spread_pips"] = {"median": round(float(spread.median()), 2), "p95": round(float(spread.quantile(0.95)), 2),
                        "p99": round(float(spread.quantile(0.99)), 2), "max": round(float(spread.max()), 1)}
    h = t.dt.hour
    r["spread_median_par_heure_utc"] = {int(k): round(float(v), 2) for k, v in spread.groupby(h.values).median().items()}
    ret = (df["bid_close"].diff() / p).abs()
    r["sauts_minute_sup_50_pips"] = int((ret > 50).sum())
    gap = t.diff().dt.total_seconds().div(60)
    wd = t.dt.weekday
    weekday_gap = (gap > 30) & (wd < 5) & ~((wd == 0) & (h < 1))
    r["trous_semaine_sup_30_min"] = int(weekday_gap.sum())
    r["plus_grands_trous_semaine"] = [f"{t.iloc[i - 1]} → {t.iloc[i]}" for i in np.argsort(-(gap.where(weekday_gap, 0).to_numpy()))[:5]
                                      if weekday_gap.iloc[i]]
    days = t.dt.date[wd < 5]
    per_day = days.value_counts()
    r["jours_ouvres"] = int(len(per_day))
    r["jours_ouvres_moins_de_1200_minutes"] = int((per_day < 1200).sum())
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--periods", nargs="*", default=PERIODS)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rep = {}
    for per in a.periods:
        for s in SYMBOLS:
            f = Path(a.data) / per / f"{s}.csv.gz"
            if not f.exists():
                rep[f"{per} {s}"] = {"absent": True}
                continue
            with gzip.open(f, "rt") as fh:
                rep[f"{per} {s}"] = check(pd.read_csv(fh), s)
            r = rep[f"{per} {s}"]
            print(f"{per} {s}: {r['lignes']:,} lignes, doublons {r['doublons_horodatage']}, OHLC incohérents "
                  f"{r['ohlc_incoherent_bid'] + r['ohlc_incoherent_ask']}, ask<bid {r['ask_sous_bid']}, spread médian "
                  f"{r['spread_pips']['median']} (p99 {r['spread_pips']['p99']}), trous >30 min en semaine "
                  f"{r['trous_semaine_sup_30_min']}, jours incomplets {r['jours_ouvres_moins_de_1200_minutes']}/{r['jours_ouvres']}, "
                  f"sauts >50 pips {r['sauts_minute_sup_50_pips']}", flush=True)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
