"""Cache du Parameter Lab.

L'analyse de marché (analyze) coûte ~95 % du temps d'un backtest. Elle est calculée UNE fois
pour toute la période, puis chaque variante de paramètres rejoue le vrai cycle (cycle.run_cycle)
en lisant ce cache au lieu de recalculer.

Par jour, deux fichiers :
- small_<jour>.pkl : pour chaque cycle et paire, le contexte allégé (dernière bougie M5 seulement)
  + les setups détectés par les stratégies avec la configuration de référence ;
- full_<jour>.pkl  : pour les cycles où une entrée est possible (sessions de trading), le contexte
  avec assez d'historique pour relancer une stratégie (Bloc C) ou changer la définition des régimes.
"""
from __future__ import annotations

import copy
import pickle
from collections import defaultdict
from datetime import datetime, timedelta
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from ..analysis.market import analyze
from ..analysis.structure import news_blackout
from ..brain.router import scan_symbol
from ..data.providers import CSVProvider, market_open_at
from ..fx import conversion_symbols
from ..scheduler import cycle_time

KEEP_FULL = {"M5": 70, "M15": 96, "M1": 3, "H1": 50}
KEEP_SMALL = {"M5": 2}

_PROV = None
_CFG = None


def cycle_times(cfg: dict, start: datetime, end: datetime) -> list[datetime]:
    """Exactement les instants de cycle de scheduler.replay."""
    step = timedelta(minutes=cfg["scheduler"]["interval_minutes"])
    now = cycle_time(start, cfg["scheduler"]["interval_minutes"])
    out = []
    while now <= end:
        if market_open_at(now, cfg["scheduler"]):
            out.append(now)
        now += step
    return out


def entry_window(now: datetime, cfg: dict) -> bool:
    """Heures où une NOUVELLE position est possible (sessions élargies d'1 h pour le Bloc B)."""
    return 5 <= now.hour < 22


def trim(ctx, keep: dict[str, int]):
    c = copy.copy(ctx)
    c.frames = {tf: df.iloc[-n:].copy() for tf, df in ctx.frames.items() if tf in keep for n in [keep[tf]]}
    return c


def _init(cfg: dict, csv_dir: str, symbols: list[str]):
    global _PROV, _CFG
    _CFG = cfg
    _PROV = CSVProvider(symbols, csv_dir)


def _day(args):
    day, times, out_dir = args
    cfg, prov = _CFG, _PROV
    small, full, setups = {}, {}, {}
    for now in times:
        for sym in cfg["symbols"]:
            try:
                raw = {tf: prov.candles(sym, tf, now, n) for tf, n in cfg["bars"].items()}
                bid, ask = prov.quote(sym, now)
                ctx = analyze(sym, raw, bid, ask, now, cfg)
            except Exception as e:                       # même comportement que le cycle réel
                small[(now, sym)] = f"données indisponibles : {e}"
                continue
            blocked, why = news_blackout(now, sym, cfg)
            ctx.news_block = why if blocked else ""
            res = scan_symbol(ctx, cfg)
            setups[(now, sym)] = res
            small[(now, sym)] = trim(ctx, KEEP_SMALL)
            if entry_window(now, cfg):
                full[(now, sym)] = trim(ctx, KEEP_FULL)
    with open(Path(out_dir) / f"small_{day}.pkl", "wb") as f:
        pickle.dump({"small": small, "scans": setups}, f, protocol=pickle.HIGHEST_PROTOCOL)
    with open(Path(out_dir) / f"full_{day}.pkl", "wb") as f:
        pickle.dump(full, f, protocol=pickle.HIGHEST_PROTOCOL)
    return day, len(times)


def build(cfg: dict, csv_dir: str | Path, out_dir: str | Path, start: datetime, end: datetime,
          workers: int = 2, log=print) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    times = cycle_times(cfg, start, end)
    by_day: dict[str, list] = defaultdict(list)
    for t in times:
        by_day[t.strftime("%Y-%m-%d")].append(t)
    todo = [(d, ts, str(out_dir)) for d, ts in sorted(by_day.items())
            if not (out_dir / f"full_{d}.pkl").exists()]
    symbols = list(cfg["symbols"]) + [s for s in conversion_symbols(cfg["symbols"], cfg["account"]["currency"])
                                      if s not in cfg["symbols"]]
    log(f"Cache : {len(times):,} cycles, {len(by_day)} jours, {len(todo)} à calculer")
    with Pool(workers, initializer=_init, initargs=(cfg, str(csv_dir), symbols)) as pool:
        for i, (d, n) in enumerate(pool.imap_unordered(_day, todo), 1):
            log(f"  {i}/{len(todo)} {d} ({n} cycles)")
    meta = {"start": str(start), "end": str(end), "cycles": len(times), "days": sorted(by_day)}
    pd.Series(meta).to_json(out_dir / "meta.json")
