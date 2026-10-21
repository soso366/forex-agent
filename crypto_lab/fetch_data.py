"""Télécharge les bougies spot publiques de Binance (data.binance.vision) et les écrit au format JSON de Freqtrade.

Aucune clé, aucun compte. Usage :
    python crypto_lab/fetch_data.py --pairs BTC/USDT ETH/USDT --timeframes 5m 1h --start 2022-12 --end 2026-09 --out user_data/data/binance
"""
import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

BASE = "https://data.binance.vision/data/spot/monthly/klines/{sym}/{tf}/{sym}-{tf}-{ym}.zip"


def months(start: str, end: str):
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    while (y, m) <= (ye, me):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            y, m = y + 1, 1


def get(url: str, tries: int = 4) -> bytes | None:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 3 * i)
        except Exception:
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"téléchargement impossible : {url}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", required=True)
    ap.add_argument("--timeframes", nargs="+", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    report = {}
    for pair in a.pairs:
        sym = pair.replace("/", "")
        for tf in a.timeframes:
            rows, missing = {}, []
            for ym in months(a.start, a.end):
                raw = get(BASE.format(sym=sym, tf=tf, ym=ym))
                if raw is None:
                    missing.append(ym)
                    continue
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    text = z.read(z.namelist()[0]).decode()
                for r in csv.reader(io.StringIO(text)):
                    if not r or not r[0].strip().isdigit():
                        continue  # en-tête éventuel
                    ts = int(r[0])
                    if ts > 10**14:  # depuis 2025, horodatage en microsecondes
                        ts //= 1000
                    rows[ts] = [ts, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])]
            data = [rows[k] for k in sorted(rows)]
            fn = os.path.join(a.out, f"{pair.replace('/', '_')}-{tf}.json")
            with open(fn, "w") as f:
                json.dump(data, f)
            report[f"{pair} {tf}"] = {"bougies": len(data), "mois_manquants": missing}
            print(f"{pair} {tf}: {len(data)} bougies, mois manquants: {missing or 'aucun'}", flush=True)
    with open(os.path.join(a.out, "_rapport_donnees.json"), "w") as f:
        json.dump(report, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
