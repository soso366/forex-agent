"""Téléchargement Dukascopy (bougies 1 minute BID/ASK) d'un CFD d'indice et construction de la table de séance New York.

Exécuté dans GitHub Actions (le poste de travail n'a pas accès à Internet). Les données brutes restent dans le cache
d'Actions : elles ne sont jamais publiées dans le dépôt.

Format bi5 : LZMA « alone », enregistrements big-endian de 24 octets (secondes depuis minuit UTC, open, close, low, high
en entiers, volume float32). Échelle des prix détectée automatiquement (PROTOCOLE.md).
"""
from __future__ import annotations

import argparse
import lzma
import random
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE = "https://datafeed.dukascopy.com/datafeed"
DT = np.dtype([("t", ">u4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")])
SCALES = (1e-3, 1e-2, 1e-1, 1.0, 1e-4, 1e-5)
NY = "America/New_York"
N_BARS = 390  # 09:30 → 15:59


def url(sym: str, d: date, side: str) -> str:
    return f"{BASE}/{sym}/{d.year:04d}/{d.month - 1:02d}/{d.day:02d}/{side}_candles_min_1.bi5"


def fetch(u: str, retries: int = 12) -> bytes | None:
    for k in range(retries):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (research)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            if data and data[:1] != b"\x5d":
                raise ConnectionError("réponse non bi5")
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if k == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if k == retries - 1:
                raise
        time.sleep(random.uniform(1, 4) * (1 + k / 3))
    return None


def download(sym: str, start: date, end: date, cache: Path, deadline: float, workers: int = 3) -> str:
    jobs = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            jobs += [(d, s) for s in ("BID", "ASK")]
        d += timedelta(days=1)

    def one(job):
        d, s = job
        p = cache / sym / f"{d:%Y}" / f"{d:%m%d}_{s}.bi5"
        if p.exists():
            return "ok"
        if time.time() > deadline:
            return "later"
        time.sleep(0.35)
        try:
            raw = fetch(url(sym, d, s))
        except Exception:
            return "err"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw or b"")
        return "ok"

    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, jobs))
    n_ok = res.count("ok")
    print(f"::notice::{sym} : {n_ok}/{len(jobs)} fichiers présents ({res.count('err')} erreurs, {res.count('later')} remis à plus tard)")
    return "COMPLETE" if n_ok == len(jobs) else "INCOMPLETE"


def decode(raw: bytes) -> np.ndarray:
    if not raw:
        return np.zeros(0, DT.newbyteorder("="))
    data = lzma.decompress(raw, format=lzma.FORMAT_ALONE)
    arr = np.frombuffer(data[: len(data) // DT.itemsize * DT.itemsize], dtype=DT)
    return arr.astype(DT.newbyteorder("="))  # ordre natif (pandas refuse le big-endian)


def build_session_table(sym: str, start: date, end: date, cache: Path) -> tuple[pd.DataFrame, float]:
    """Une ligne par minute de séance New York : jour, n° de minute (0 = 09:30), bid/ask open/close, mid h/l/c, volume."""
    frames = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            parts = {}
            for s in ("BID", "ASK"):
                p = cache / sym / f"{d:%Y}" / f"{d:%m%d}_{s}.bi5"
                parts[s] = decode(p.read_bytes()) if p.exists() else np.zeros(0, DT.newbyteorder("="))
            if len(parts["BID"]) and len(parts["ASK"]):
                b = pd.DataFrame(parts["BID"]).set_index("t")
                a = pd.DataFrame(parts["ASK"]).set_index("t")
                m = b.join(a, lsuffix="_b", rsuffix="_a", how="inner")
                m = m[(m.v_b > 0) | (m.v_a > 0) | (m.o_b != m.c_b)]
                ts = pd.Timestamp(d, tz="UTC") + pd.to_timedelta(m.index.astype(np.int64), unit="s")
                loc = ts.tz_convert(NY)
                mins = (loc.hour * 60 + loc.minute) - (9 * 60 + 30)
                keep = (mins >= 0) & (mins < N_BARS)
                if keep.any():
                    m = m[keep]
                    frames.append(pd.DataFrame({
                        "jour": loc[keep].strftime("%Y-%m-%d"), "m": np.asarray(mins[keep]),
                        "bo": m.o_b.values, "bc": m.c_b.values, "ao": m.o_a.values, "ac": m.c_a.values,
                        "h": (m.h_b.values + m.h_a.values) / 2, "l": (m.l_b.values + m.l_a.values) / 2,
                        "v": m.v_b.values + m.v_a.values}))
        d += timedelta(days=1)
    df = pd.concat(frames, ignore_index=True)
    med = float(np.median(df["bc"]))
    scale = next(s for s in SCALES if 500 <= med * s <= 20000)
    for c in ("bo", "bc", "ao", "ac", "h", "l"):
        df[c] = df[c] * scale
    return df, scale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="USA500IDXUSD")
    ap.add_argument("--start", default="2015-12-01")
    ap.add_argument("--end", default="2026-10-23")
    ap.add_argument("--cache", default="data/duka")
    ap.add_argument("--budget-min", type=float, default=300)
    ap.add_argument("--out", default="data/session.csv.gz")
    ap.add_argument("--status", default="data/status.txt")
    a = ap.parse_args()
    s, e = date.fromisoformat(a.start), date.fromisoformat(a.end)
    status = download(a.sym, s, e, Path(a.cache), time.time() + a.budget_min * 60)
    Path(a.status).parent.mkdir(parents=True, exist_ok=True)
    Path(a.status).write_text(status + "\n")
    if status == "COMPLETE":
        df, scale = build_session_table(a.sym, s, e, Path(a.cache))
        df.to_csv(a.out, index=False)
        print(f"::notice::table de séance : {len(df):,} minutes, {df.jour.nunique()} jours, échelle {scale}, "
              f"prix {df.bc.iloc[0]:.1f} → {df.bc.iloc[-1]:.1f}, écart médian {float((df.ac - df.bc).median()):.2f} pt")


if __name__ == "__main__":
    main()
