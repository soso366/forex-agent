"""Scheduler : relance l'agent toutes les 5 minutes, sans intervention humaine.

- run_once() : un cycle, protégé par un verrou (utilisé par cron/systemd)
- loop()     : boucle intégrée alignée sur :00, :05, :10… (+ délai de clôture de bougie)
- replay()   : même code, horloge simulée avançant de 5 min (tests / rejeu historique)
"""
from __future__ import annotations

import fcntl
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from .config import resolve_path
from .cycle import run_cycle
from .data.providers import DataProvider, make_provider, market_open_at
from .journal import Store

log = logging.getLogger("forex_agent")


def next_run(now: datetime, interval_min: int, delay_s: int) -> datetime:
    """Prochain créneau aligné : 10:00:15, 10:05:15, 10:10:15…"""
    base = now.replace(second=0, microsecond=0)
    minutes = (base.minute // interval_min + 1) * interval_min
    slot = base.replace(minute=0) + timedelta(minutes=minutes, seconds=delay_s)
    if slot - timedelta(minutes=interval_min) > now:      # on est avant le délai du créneau courant
        slot -= timedelta(minutes=interval_min)
    return slot


def cycle_time(now: datetime, interval_min: int) -> datetime:
    """Heure logique du cycle (bord du créneau de 5 min)."""
    base = now.replace(second=0, microsecond=0)
    return base - timedelta(minutes=base.minute % interval_min)


@contextmanager
def single_instance(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("un cycle est déjà en cours (verrou actif)")
        yield


def open_store(cfg: dict) -> Store:
    return Store(resolve_path(cfg, "db"), resolve_path(cfg, "jsonl"))


def run_once(cfg: dict, now: datetime | None = None, provider: DataProvider | None = None) -> dict:
    now = cycle_time(now or datetime.now(timezone.utc), cfg["scheduler"]["interval_minutes"])
    with single_instance(resolve_path(cfg, "lock")):
        provider = provider or make_provider(cfg, now)
        store = open_store(cfg)
        try:
            return run_cycle(cfg, provider, store, now)
        finally:
            store.close()


def loop(cfg: dict, max_cycles: int | None = None) -> None:
    sc = cfg["scheduler"]
    provider = None
    done = 0
    while max_cycles is None or done < max_cycles:
        target = next_run(datetime.now(timezone.utc), sc["interval_minutes"], sc["delay_seconds"])
        time.sleep(max(0.0, (target - datetime.now(timezone.utc)).total_seconds()))
        now = datetime.now(timezone.utc)
        if not market_open_at(now, sc):
            log.info("%s marché fermé — cycle sauté", now.isoformat())
            continue
        try:
            if provider is None:
                provider = make_provider(cfg, now)
            rec = run_once(cfg, now, provider)
            log.info("%s capital %.2f | %s", rec["ts"], rec["equity"], rec["summary"])
        except Exception as e:                    # jamais d'arrêt de la boucle
            log.exception("cycle en erreur : %s", e)
        done += 1


def replay(cfg: dict, start: datetime, end: datetime, provider: DataProvider | None = None,
           verbose: bool = False, keep_records: bool = True, progress: bool = False) -> list[dict] | int:
    """Rejoue le fonctionnement autonome sur une période : un cycle toutes les 5 min simulées.
    Même code que le fonctionnement réel (run_cycle) ; seule l'horloge est simulée."""
    import sys
    import time as _time
    provider = provider or make_provider(cfg)
    store = open_store(cfg)
    step = timedelta(minutes=cfg["scheduler"]["interval_minutes"])
    now = cycle_time(start, cfg["scheduler"]["interval_minutes"])
    records, count, day, t0 = [], 0, None, _time.time()
    try:
        while now <= end:
            if market_open_at(now, cfg["scheduler"]):
                rec = run_cycle(cfg, provider, store, now)
                count += 1
                if keep_records:
                    records.append(rec)
                if verbose and rec["summary"] != "NO TRADE sur toutes les paires":
                    print(f"{rec['ts'][:16]}  {rec['equity']:8.2f} €  {rec['summary']}")
                if progress and now.date() != day:
                    day = now.date()
                    ntr = store.db.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
                    print(f"[{_time.time() - t0:6.0f} s] {day}  cycles {count:,}  trades {ntr}  "
                          f"capital {rec['equity']:.2f}", file=sys.stderr, flush=True)
            now += step
    finally:
        store.close()
    return records if keep_records else count
