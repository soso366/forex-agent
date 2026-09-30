"""Sources de données de marché.

Toutes les sources exposent la même interface (DataProvider) :
- candles(symbol, tf, now, count) : bougies CLÔTURÉES uniquement (open + durée <= now)
- quote(symbol, now)              : prix bid/ask courant
- m1(symbol, start, end)          : bougies M1 dont l'ouverture est dans [start, end)

Format interne (index = heure d'OUVERTURE de bougie, UTC) :
  o, h, l, c       -> prix BID
  ao, ah, al, ac   -> prix ASK
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240}
COLS = ["o", "h", "l", "c", "ao", "ah", "al", "ac"]
AGG = {"o": "first", "h": "max", "l": "min", "c": "last",
       "ao": "first", "ah": "max", "al": "min", "ac": "last"}


def floor_minute(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0)


def market_open_at(ts: pd.Timestamp | datetime, cfg_sched: dict | None = None) -> bool:
    """Forex ouvert hors week-end (ven. 21:00 UTC -> dim. 21:00 UTC par défaut)."""
    close = (cfg_sched or {}).get("weekly_close", {"weekday": 4, "hour": 21})
    open_ = (cfg_sched or {}).get("weekly_open", {"weekday": 6, "hour": 21})
    wd, hr = ts.weekday(), ts.hour
    if wd == close["weekday"] and hr >= close["hour"]:
        return False
    if wd == 5:
        return False
    if wd == open_["weekday"] and hr < open_["hour"]:
        return False
    return True


def resample(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    if tf == "M1":
        return m1
    out = m1.resample(f"{TF_MINUTES[tf]}min", label="left", closed="left").agg(AGG)
    return out.dropna(subset=["o"])


def validate_m1(df: pd.DataFrame, symbol: str) -> None:
    """Contrôles de cohérence avant usage (données importées ou générées)."""
    problems = []
    if not df.index.is_monotonic_increasing:
        problems.append("ordre chronologique")
    if df.index.has_duplicates:
        problems.append("doublons")
    if (df["h"] < df[["o", "c"]].max(axis=1) - 1e-12).any() or (df["l"] > df[["o", "c"]].min(axis=1) + 1e-12).any():
        problems.append("OHLC bid incohérent")
    if (df["ac"] < df["c"] - 1e-12).any():
        problems.append("ask < bid")
    if problems:
        raise ValueError(f"{symbol}: données invalides ({', '.join(problems)})")


class DataProvider(ABC):
    @abstractmethod
    def candles(self, symbol: str, tf: str, now: datetime, count: int) -> pd.DataFrame: ...

    @abstractmethod
    def quote(self, symbol: str, now: datetime) -> tuple[float, float]: ...

    @abstractmethod
    def m1(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame: ...

    def has(self, symbol: str) -> bool:
        return True


class InMemoryProvider(DataProvider):
    """Base pour les sources rejouées (synthétique, CSV). Pré-calcule les resamplings ;
    seules les bougies clôturées à `now` sont renvoyées, donc aucun look-ahead."""

    def __init__(self, frames: dict[str, pd.DataFrame]):
        self._m1 = {}
        for s, df in frames.items():
            validate_m1(df, s)
            self._m1[s] = df
        self._cache: dict[tuple[str, str], pd.DataFrame] = {}

    def has(self, symbol: str) -> bool:
        return symbol in self._m1

    def _frame(self, symbol: str, tf: str) -> pd.DataFrame:
        key = (symbol, tf)
        if key not in self._cache:
            self._cache[key] = resample(self._m1[symbol], tf)
        return self._cache[key]

    def candles(self, symbol, tf, now, count):
        df = self._frame(symbol, tf)
        last_open_allowed = pd.Timestamp(now) - pd.Timedelta(minutes=TF_MINUTES[tf])
        end = df.index.searchsorted(last_open_allowed, side="right")
        return df.iloc[max(0, end - count):end]

    def quote(self, symbol, now):
        df = self._m1[symbol]
        ts = pd.Timestamp(floor_minute(now))
        i = df.index.searchsorted(ts, side="left")
        if i < len(df) and df.index[i] == ts:
            row = df.iloc[i]
            return float(row["o"]), float(row["ao"])
        if i == 0:
            raise LookupError(f"Pas de prix pour {symbol} à {now}")
        row = df.iloc[i - 1]
        return float(row["c"]), float(row["ac"])

    def m1(self, symbol, start, end):
        df = self._m1[symbol]
        a = df.index.searchsorted(pd.Timestamp(start), side="left")
        b = df.index.searchsorted(pd.Timestamp(end), side="left")
        return df.iloc[a:b]

    def time_range(self) -> tuple[datetime, datetime]:
        first = max(df.index[0] for df in self._m1.values())
        last = min(df.index[-1] for df in self._m1.values())
        return first.to_pydatetime(), last.to_pydatetime()


# ---------------------------------------------------------------- synthétique
SYNTH_PARAMS = {  # prix de départ, volatilité / minute (en pips), spread (pips) session active / Asie
    "EURUSD": (1.1700, 0.55, 0.8, 1.4),
    "GBPUSD": (1.3400, 0.75, 1.2, 2.2),
    "USDJPY": (148.00, 0.70, 0.9, 1.6),
    "AUDUSD": (0.6600, 0.50, 1.0, 1.6),
    "EURGBP": (0.8700, 0.40, 1.1, 1.8),
}


def synthetic_m1(symbol: str, start: datetime, end: datetime, seed: int = 7) -> pd.DataFrame:
    """Marché simulé avec alternance de régimes (tendance, range, chop, spikes)
    pour tester la boucle complète hors connexion. Ce n'est PAS un vrai marché."""
    from .. import fx
    p0, vol_pips, spr_active, spr_asia = SYNTH_PARAMS.get(symbol, (1.0, 0.6, 1.0, 1.8))
    pip = fx.pip_size(symbol)
    rng = np.random.default_rng(seed + sum(map(ord, symbol)))
    idx = pd.date_range(pd.Timestamp(start).floor("min"), pd.Timestamp(end).floor("min"),
                        freq="min", tz="UTC", inclusive="left")
    wd, hr = idx.weekday.to_numpy(), idx.hour.to_numpy()
    closed = ((wd == 4) & (hr >= 21)) | (wd == 5) | ((wd == 6) & (hr < 21))
    idx = idx[~closed]
    n = len(idx)
    hours = idx.hour.to_numpy()
    session = np.where((hours >= 7) & (hours < 17), 1.25, np.where((hours >= 12) & (hours < 20), 1.1, 0.6))
    sigma = vol_pips * pip * session

    closes = np.empty(n)
    price, i = p0, 0
    while i < n:
        seg = int(rng.integers(60, 480))
        kind = rng.choice(["trend", "range", "chop"], p=[0.4, 0.35, 0.25])
        drift = rng.choice([-1, 1]) * rng.uniform(0.12, 0.30)
        anchor = price
        for j in range(i, min(n, i + seg)):
            eps = rng.standard_normal() * sigma[j]
            if kind == "trend":
                price += drift * sigma[j] + eps
            elif kind == "range":
                price += 0.04 * (anchor - price) + eps * 0.9
            else:
                price += eps * 1.4
            if rng.random() < 0.0008:              # spike ponctuel
                price += rng.choice([-1, 1]) * sigma[j] * rng.uniform(5, 12)
            closes[j] = price
        i += seg

    opens = np.concatenate([[p0], closes[:-1]])
    wick = np.abs(rng.standard_normal((2, n))) * sigma * 0.6
    highs = np.maximum(opens, closes) + wick[0]
    lows = np.minimum(opens, closes) - wick[1]
    spread = np.where(session < 1.0, spr_asia, spr_active) * pip * (1 + rng.exponential(0.15, n))
    dec = 3 if pip == 0.01 else 5
    df = pd.DataFrame({"o": opens, "h": highs, "l": lows, "c": closes}, index=idx).round(dec)
    df["h"] = df[["o", "h", "c"]].max(axis=1)
    df["l"] = df[["o", "l", "c"]].min(axis=1)
    spread = np.round(spread, dec)
    for b, a in zip(["o", "h", "l", "c"], ["ao", "ah", "al", "ac"]):
        df[a] = (df[b] + spread).round(dec)
    df.index.name = "time"
    return df


class SyntheticProvider(InMemoryProvider):
    def __init__(self, symbols: list[str], start: datetime, end: datetime, seed: int = 7):
        super().__init__({s: synthetic_m1(s, start, end, seed) for s in symbols})


# ---------------------------------------------------------------------- CSV
class CSVProvider(InMemoryProvider):
    """CSV M1 (ex. export Dukascopy converti) : <csv_dir>/<SYMBOL>.csv avec colonnes
    time (UTC, ouverture de bougie), bid_open, bid_high, bid_low, bid_close,
    ask_open, ask_high, ask_low, ask_close."""

    RENAME = {"bid_open": "o", "bid_high": "h", "bid_low": "l", "bid_close": "c",
              "ask_open": "ao", "ask_high": "ah", "ask_low": "al", "ask_close": "ac"}

    def __init__(self, symbols: list[str], csv_dir: str | Path):
        frames = {}
        for s in symbols:
            path = Path(csv_dir) / f"{s}.csv"
            df = pd.read_csv(path)
            df["time"] = pd.to_datetime(df["time"], utc=True)
            frames[s] = df.set_index("time").rename(columns=self.RENAME)[COLS].astype(float)
        super().__init__(frames)


# -------------------------------------------------------------------- OANDA
class OandaProvider(DataProvider):
    """Prix temps réel en LECTURE SEULE depuis l'API OANDA (compte démo).
    Aucun ordre n'est jamais envoyé : l'exécution reste dans le PaperBroker.
    Non testé dans cet environnement (pas d'accès réseau) : à valider à la première mise en route."""

    HOSTS = {"practice": "https://api-fxpractice.oanda.com", "live": "https://api-fxtrade.oanda.com"}
    GRAN = {"M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30", "H1": "H1", "H4": "H4"}

    def __init__(self, token: str, environment: str = "practice"):
        self.token, self.host = token, self.HOSTS[environment]

    @classmethod
    def from_config(cls, cfg: dict) -> "OandaProvider":
        o = cfg["data"]["oanda"]
        token = os.environ.get(o.get("token_env", "OANDA_TOKEN"))
        if not token:
            raise RuntimeError("Variable d'environnement OANDA_TOKEN absente")
        return cls(token, o.get("environment", "practice"))

    def _get(self, symbol: str, params: dict) -> pd.DataFrame:
        inst = f"{symbol[:3]}_{symbol[3:]}"
        url = f"{self.host}/v3/instruments/{inst}/candles?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        rows = []
        for c in data.get("candles", []):
            b, a = c["bid"], c["ask"]
            rows.append({"time": pd.Timestamp(c["time"]), "complete": c["complete"],
                         "o": float(b["o"]), "h": float(b["h"]), "l": float(b["l"]), "c": float(b["c"]),
                         "ao": float(a["o"]), "ah": float(a["h"]), "al": float(a["l"]), "ac": float(a["c"])})
        if not rows:
            return pd.DataFrame(columns=COLS + ["complete"])
        return pd.DataFrame(rows).set_index("time")

    def candles(self, symbol, tf, now, count):
        df = self._get(symbol, {"granularity": self.GRAN[tf], "count": count + 1, "price": "BA"})
        df = df[df["complete"]]
        limit = pd.Timestamp(now) - pd.Timedelta(minutes=TF_MINUTES[tf])
        return df[df.index <= limit][COLS].tail(count)

    def quote(self, symbol, now):
        df = self._get(symbol, {"granularity": "S5", "count": 1, "price": "BA"})
        row = df.iloc[-1]
        return float(row["c"]), float(row["ac"])

    def m1(self, symbol, start, end):
        df = self._get(symbol, {"granularity": "M1", "price": "BA",
                                "from": pd.Timestamp(start).isoformat(), "to": pd.Timestamp(end).isoformat()})
        return df[df["complete"]][COLS]


def make_provider(cfg: dict, now: datetime | None = None) -> DataProvider:
    from ..fx import conversion_symbols
    symbols = list(cfg["symbols"]) + conversion_symbols(cfg["symbols"], cfg["account"]["currency"])
    kind = cfg["data"]["provider"]
    if kind == "synthetic":
        sc = cfg["data"]["synthetic"]
        start = pd.Timestamp(sc["start"], tz="UTC").to_pydatetime()
        end = start + timedelta(days=sc["days"])
        if now is not None:
            end = max(end, now + timedelta(days=1))
        return SyntheticProvider(symbols, start, end, sc.get("seed", 7))
    if kind == "csv":
        from ..config import ROOT
        d = Path(cfg["data"]["csv_dir"])
        return CSVProvider(symbols, d if d.is_absolute() else ROOT / d)
    if kind == "oanda":
        return OandaProvider.from_config(cfg)
    raise ValueError(f"Provider inconnu : {kind}")
