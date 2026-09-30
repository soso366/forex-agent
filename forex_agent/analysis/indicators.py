"""Indicateurs techniques (calculés uniquement sur des bougies clôturées)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _ema_np(x: np.ndarray, n: int) -> np.ndarray:
    a = 2.0 / (n + 1)
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


def _wilder_np(x: np.ndarray, n: int) -> np.ndarray:
    a = 1.0 / n
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


def to_mid(df: pd.DataFrame) -> pd.DataFrame:
    """Bougies mid (moyenne bid/ask) pour l'analyse."""
    return pd.DataFrame({b: (df[b].to_numpy() + df[a].to_numpy()) / 2
                         for b, a in (("o", "ao"), ("h", "ah"), ("l", "al"), ("c", "ac"))},
                        index=df.index)


def ema(s: pd.Series, n: int) -> pd.Series:
    return pd.Series(_ema_np(s.to_numpy(dtype=float), n), index=s.index)


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    return pd.Series(_rsi_np(close.to_numpy(dtype=float), n), index=close.index)


def _rsi_np(c: np.ndarray, n: int) -> np.ndarray:
    d = np.diff(c, prepend=c[0])
    up = _wilder_np(np.clip(d, 0, None), n)
    down = _wilder_np(np.clip(-d, 0, None), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + up / down)
    r[down == 0] = np.where(up[down == 0] > 0, 100.0, 50.0)
    return r


def _atr_np(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int) -> np.ndarray:
    prev = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    return _wilder_np(tr, n)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return pd.Series(_atr_np(df["h"].to_numpy(float), df["l"].to_numpy(float),
                             df["c"].to_numpy(float), n), index=df.index)


def efficiency_ratio(close: pd.Series, n: int = 20) -> float:
    """|déplacement net| / somme des mouvements : ~1 = tendance propre, ~0 = bruit."""
    if len(close) <= n:
        return 0.0
    c = close.iloc[-(n + 1):]
    path = c.diff().abs().sum()
    return float(abs(c.iloc[-1] - c.iloc[0]) / path) if path > 0 else 0.0


def swings(df: pd.DataFrame, left: int = 2, right: int = 2) -> tuple[list[tuple], list[tuple]]:
    """Swing highs / lows confirmés (fractales). Un swing n'existe qu'une fois `right`
    bougies clôturées après lui : pas de look-ahead."""
    h, l = df["h"], df["l"]
    win = left + right + 1
    # fenêtre [i-left, i+right] ; les `right` dernières bougies ne peuvent pas être des swings
    hmax = h.rolling(win).max().shift(-right)
    lmin = l.rolling(win).min().shift(-right)
    prev_h = h.shift(1).rolling(left).max()
    prev_l = l.shift(1).rolling(left).min()
    is_h = (h == hmax) & (h > prev_h)
    is_l = (l == lmin) & (l < prev_l)
    highs = [(t, float(v)) for t, v in h[is_h].items()]
    lows = [(t, float(v)) for t, v in l[is_l].items()]
    return highs, lows


def add_basics(df: pd.DataFrame) -> pd.DataFrame:
    """Bougies mid + EMA9/20/50, RSI14, ATR14 (une seule construction de DataFrame)."""
    o, h, l, c = (df[k].to_numpy(dtype=float) for k in ("o", "h", "l", "c"))
    return pd.DataFrame({
        "o": o, "h": h, "l": l, "c": c,
        "ema9": _ema_np(c, 9), "ema20": _ema_np(c, 20), "ema50": _ema_np(c, 50),
        "rsi": _rsi_np(c, 14), "atr": _atr_np(h, l, c, 14),
    }, index=df.index)


def macd_hist(close: pd.Series) -> pd.Series:
    """Histogramme MACD 12/26/9 (Trading Rush : filtre de momentum, jamais signal seul)."""
    c = close.to_numpy(dtype=float)
    line = _ema_np(c, 12) - _ema_np(c, 26)
    return pd.Series(line - _ema_np(line, 9), index=close.index)
