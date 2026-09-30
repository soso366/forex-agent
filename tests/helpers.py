"""Outils communs aux tests (stdlib unittest : `python -m unittest discover -s tests`)."""
from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forex_agent.config import Setup, load_config  # noqa: E402
from forex_agent.data.providers import InMemoryProvider  # noqa: E402
from forex_agent.journal import Store  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 9, 9, 10, 0, tzinfo=UTC)   # mercredi, session active


def tmp_cfg(**over) -> dict:
    d = Path(tempfile.mkdtemp())
    base = {"paths": {"db": str(d / "j.sqlite"), "jsonl": str(d / "c.jsonl"),
                      "kill_switch": str(d / "KILL"), "lock": str(d / "lock")}}
    for k, v in over.items():
        base[k] = v
    return load_config(overrides=base)


def flat_m1(symbol: str, start: datetime, minutes: int, price: float, spread: float,
            path: list[tuple[float, float, float, float]] | None = None) -> pd.DataFrame:
    """M1 plat, ou suivant `path` = liste de (o, h, l, c) bid pour les premières minutes."""
    idx = pd.date_range(start, periods=minutes, freq="min", tz="UTC")
    o = np.full(minutes, price); h = o.copy(); l = o.copy(); c = o.copy()
    for i, (po, ph, pl, pc) in enumerate(path or []):
        o[i], h[i], l[i], c[i] = po, ph, pl, pc
    if path:
        o[len(path):] = h[len(path):] = l[len(path):] = c[len(path):] = path[-1][3]
    df = pd.DataFrame({"o": o, "h": h, "l": l, "c": c}, index=idx)
    for b, a in zip("ohlc", ["ao", "ah", "al", "ac"]):
        df[a] = df[b] + spread
    return df


def simple_provider(start: datetime = T0 - timedelta(hours=1), minutes: int = 240, **paths) -> InMemoryProvider:
    frames = {
        "EURUSD": flat_m1("EURUSD", start, minutes, 1.17000, 0.00010, paths.get("EURUSD")),
        "GBPUSD": flat_m1("GBPUSD", start, minutes, 1.34000, 0.00012, paths.get("GBPUSD")),
        "USDJPY": flat_m1("USDJPY", start, minutes, 148.000, 0.010, paths.get("USDJPY")),
    }
    return InMemoryProvider(frames)


def store_for(cfg: dict, capital: float = 50.0) -> Store:
    s = Store(cfg["paths"]["db"], cfg["paths"]["jsonl"])
    s.init_account("EUR", 50.0, T0)
    if capital != 50.0:
        s.set_balance(capital, capital)
    return s


def setup(symbol="EURUSD", direction="BUY", entry=1.17010, stop=1.16960, target=1.17310) -> Setup:
    return Setup(symbol=symbol, direction=direction, strategy="Test_v1", entry=entry, stop=stop,
                 target=target, confirmations={k: True for k in
                                               ("context", "structure", "location", "momentum",
                                                "trigger", "room", "rr", "spread")}, id="x")


MIDS = {"EURUSD": 1.17005, "GBPUSD": 1.34006, "USDJPY": 148.005}
