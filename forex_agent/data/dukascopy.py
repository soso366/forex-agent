"""Données historiques Dukascopy → CSV M1 bid/ask au format de CSVProvider.

Source : https://datafeed.dukascopy.com/datafeed/<SYMBOL>/<AAAA>/<MM-1>/<JJ>/<SIDE>_candles_min_1.bi5
- un fichier par JOUR (UTC) et par côté (BID / ASK), 1440 bougies M1 ;
- compression LZMA « alone » ; enregistrements big-endian de 24 octets :
  secondes depuis minuit UTC (uint32), open, close, low, high (int32, en points), volume (float32) ;
- point = 1e-5 (1e-3 pour les paires en JPY) ;
- les minutes sans cotation (week-end, fermeture) apparaissent comme bougies plates à volume 0 :
  elles sont RETIRÉES (une minute est gardée si BID ou ASK a eu une activité).

Chaîne : téléchargement (cache local, reprise possible) → décodage → fusion BID+ASK
→ contrôles de cohérence → data/m1/<SYMBOL>.csv + rapport qualité JSON.
Aucune donnée n'est modifiée pour « améliorer » les résultats : les minutes incohérentes
sont comptées et exclues, jamais corrigées.
"""
from __future__ import annotations

import json
import lzma
import struct
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

BASE_URL = "https://datafeed.dukascopy.com/datafeed"
RECORD = struct.Struct(">Iiiiif")   # 24 octets : temps, open, close, low, high, volume
SIDES = ("BID", "ASK")


def point(symbol: str) -> float:
    return 1e-3 if symbol.endswith("JPY") else 1e-5


def day_url(symbol: str, day: date, side: str) -> str:
    return f"{BASE_URL}/{symbol}/{day.year:04d}/{day.month - 1:02d}/{day.day:02d}/{side}_candles_min_1.bi5"


def cache_path(cache_dir: Path, symbol: str, day: date, side: str) -> Path:
    return cache_dir / symbol / f"{day:%Y}" / f"{day:%m}" / f"{day:%d}_{side}.bi5"


def decode_bi5(raw: bytes, day: date, symbol: str) -> pd.DataFrame:
    """Décode un fichier bi5 de bougies M1 → DataFrame (index UTC = ouverture de bougie)."""
    cols = ["o", "h", "l", "c", "vol"]
    if not raw:
        return pd.DataFrame(columns=cols, index=pd.DatetimeIndex([], tz="UTC", name="time"))
    data = lzma.decompress(raw, format=lzma.FORMAT_ALONE)
    n = len(data) // RECORD.size
    arr = np.frombuffer(data[: n * RECORD.size], dtype=np.dtype([
        ("t", ">u4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")]))
    p = point(symbol)
    base = pd.Timestamp(day, tz="UTC")
    idx = base + pd.to_timedelta(arr["t"].astype(np.int64), unit="s")
    df = pd.DataFrame({"o": arr["o"] * p, "h": arr["h"] * p, "l": arr["l"] * p, "c": arr["c"] * p,
                       "vol": arr["v"].astype(float)}, index=pd.DatetimeIndex(idx, name="time"))
    return df


class RateLimited(Exception):
    """Dukascopy a demandé de ralentir (HTTP 429/503) et la patience est épuisée pour ce fichier."""


_pace_lock = __import__("threading").Lock()
_next_slot = [0.0]
MIN_INTERVAL = 0.6          # au plus ~1,6 requête/seconde, tous fils confondus


def _wait_turn(extra: float = 0.0) -> None:
    """Espace les requêtes ; une pause imposée par le serveur s'applique à tous les fils."""
    with _pace_lock:
        now = time.monotonic()
        slot = max(_next_slot[0], now) + extra
        _next_slot[0] = slot + MIN_INTERVAL
    delay = slot - time.monotonic()
    if delay > 0:
        time.sleep(delay)


def fetch(url: str, retries: int = 8, timeout: int = 30) -> bytes | None:
    """Télécharge une URL en respectant les limites de Dukascopy.
    404 = jour sans données → None. 429/503 = on ralentit (Retry-After ou 15 s, 30 s, 60 s… max 5 min)."""
    backoff = 15.0
    for attempt in range(retries):
        _wait_turn()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "forex-agent-research/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            if data and data[:1] != b"\x5d":            # pas un fichier LZMA : page d'erreur, on ne la garde pas
                raise ConnectionError(f"réponse inattendue ({len(data)} octets, pas au format bi5)")
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                if e.code in (429, 503):
                    raise RateLimited(f"HTTP {e.code} (limite de débit Dukascopy)") from e
                raise
            if e.code in (429, 503):
                ra = e.headers.get("Retry-After") if e.headers else None
                wait = float(ra) if ra and ra.isdigit() else backoff
                _wait_turn(extra=min(wait, 300))        # tout le monde attend
                backoff = min(backoff * 2, 300)
                continue
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries - 1:
                raise
        time.sleep(min(2 ** attempt, 60))
    return None


def download(symbols: list[str], start: date, end: date, cache_dir: Path,
             fetcher: Callable[[str], bytes | None] = fetch, workers: int = 2,
             log: Callable[[str], None] = print) -> dict:
    """Télécharge [start, end] inclus dans le cache ; les fichiers déjà présents ne sont pas retéléchargés."""
    jobs = []
    d = start
    while d <= end:
        if d.weekday() != 5:                           # samedi : jamais de cotation
            for s in symbols:
                for side in SIDES:
                    jobs.append((s, d, side))
        d += timedelta(days=1)
    stats = {"requested": len(jobs), "cached": 0, "downloaded": 0, "missing": 0, "errors": []}

    def one(job):
        s, d, side = job
        path = cache_path(cache_dir, s, d, side)
        if path.exists():
            return "cached"
        try:
            raw = fetcher(day_url(s, d, side))
        except Exception as e:                         # on continue, l'erreur est rapportée
            return f"error:{s} {d} {side}: {e}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw or b"")                   # fichier vide = jour sans données (évite de redemander)
        return "downloaded" if raw else "missing"

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(one, jobs):
            done += 1
            if res.startswith("error"):
                stats["errors"].append(res[6:])
            else:
                stats[res] += 1
            if done % 100 == 0 or done == len(jobs):
                log(f"  {done}/{len(jobs)} fichiers ({stats['downloaded']} téléchargés, "
                    f"{stats['cached']} en cache, {len(stats['errors'])} erreurs)")
    return stats


def build_symbol(symbol: str, start: date, end: date, cache_dir: Path) -> tuple[pd.DataFrame, dict]:
    """Fusionne BID + ASK depuis le cache → M1 au format interne + statistiques de qualité."""
    frames = []
    q = {"symbol": symbol, "days_with_data": 0, "days_missing_side": [], "flat_minutes_removed": 0,
         "ask_below_bid_removed": 0, "ohlc_invalid_removed": 0}
    d = start
    while d <= end:
        sides = {}
        for side in SIDES:
            p = cache_path(cache_dir, symbol, d, side)
            if p.exists():
                sides[side] = decode_bi5(p.read_bytes(), d, symbol)
        d_ok = all(side in sides and len(sides[side]) for side in SIDES)
        if not d_ok:
            if any(side in sides and len(sides[side]) for side in SIDES):
                q["days_missing_side"].append(str(d))
            d += timedelta(days=1)
            continue
        b, a = sides["BID"], sides["ASK"]
        m = b.join(a, how="inner", rsuffix="_a")
        active = (m["vol"] > 0) | (m["vol_a"] > 0)
        q["flat_minutes_removed"] += int((~active).sum())
        m = m[active]
        if len(m):
            q["days_with_data"] += 1
            frames.append(pd.DataFrame({
                "bid_open": m["o"], "bid_high": m["h"], "bid_low": m["l"], "bid_close": m["c"],
                "ask_open": m["o_a"], "ask_high": m["h_a"], "ask_low": m["l_a"], "ask_close": m["c_a"],
            }))
        d += timedelta(days=1)
    if not frames:
        return pd.DataFrame(), q
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    dec = 3 if symbol.endswith("JPY") else 5
    df = df.round(dec)
    bad_ohlc = (df["bid_high"] < df[["bid_open", "bid_close"]].max(axis=1)) | \
               (df["bid_low"] > df[["bid_open", "bid_close"]].min(axis=1)) | \
               (df["ask_high"] < df[["ask_open", "ask_close"]].max(axis=1)) | \
               (df["ask_low"] > df[["ask_open", "ask_close"]].min(axis=1))
    q["ohlc_invalid_removed"] = int(bad_ohlc.sum())
    if bad_ohlc.mean() > 0.01:                          # > 1 % : ce n'est pas du bruit, c'est un format mal lu
        raise ValueError(f"{symbol}: {bad_ohlc.mean():.1%} de bougies OHLC incohérentes — "
                         "format bi5 inattendu, arrêt (aucune donnée n'est « corrigée »)")
    df = df[~bad_ohlc]
    bad_spread = (df["ask_close"] < df["bid_close"]) | (df["ask_open"] < df["bid_open"])
    q["ask_below_bid_removed"] = int(bad_spread.sum())
    df = df[~bad_spread]
    pip = 0.01 if symbol.endswith("JPY") else 0.0001
    spread = (df["ask_close"] - df["bid_close"]) / pip
    gaps = df.index.to_series().diff().dt.total_seconds().div(60)
    q.update({
        "rows": int(len(df)), "first": str(df.index[0]), "last": str(df.index[-1]),
        "spread_pips": {"median": round(float(spread.median()), 2), "p95": round(float(spread.quantile(0.95)), 2),
                        "max": round(float(spread.max()), 2)},
        "gaps_over_15min_weekdays": int(((gaps > 15) & (df.index.weekday < 5)).sum()),
    })
    return df, q


def write_csv(df: pd.DataFrame, out_dir: Path, symbol: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{symbol}.csv"
    out = df.copy()
    out.index = out.index.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.index.name = "time"
    out.to_csv(path)
    return path


def prepare(symbols: list[str], start: date, end: date, cache_dir: Path, out_dir: Path,
            fetcher: Callable[[str], bytes | None] = fetch, workers: int = 2,
            log: Callable[[str], None] = print) -> dict:
    """Chaîne complète : téléchargement → conversion → validation → CSV + rapport qualité."""
    from .providers import CSVProvider
    log(f"Téléchargement Dukascopy {', '.join(symbols)} du {start} au {end} (BID + ASK, M1)")
    dl = download(symbols, start, end, cache_dir, fetcher, workers, log)
    report = {"download": dl, "symbols": {}}
    for s in symbols:
        df, q = build_symbol(s, start, end, cache_dir)
        if df.empty:
            q["error"] = "aucune donnée"
            report["symbols"][s] = q
            log(f"  {s} : AUCUNE DONNÉE")
            continue
        write_csv(df, out_dir, s)
        report["symbols"][s] = q
        log(f"  {s} : {q['rows']:,} minutes, {q['days_with_data']} jours, spread médian "
            f"{q['spread_pips']['median']} pips, {q['flat_minutes_removed']:,} minutes plates retirées")
    ok = [s for s in symbols if "error" not in report["symbols"][s]]
    if ok:
        CSVProvider(ok, out_dir)                        # relit et valide exactement comme le rejeu
        report["validated_with_csvprovider"] = ok
        log(f"Validation CSVProvider OK : {', '.join(ok)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "quality_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report
