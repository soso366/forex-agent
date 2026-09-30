"""Briques de lecture du prix issues des documents sources.

- structure_trend : tendance OBJECTIVE (vidéo « The only technical analysis video ») :
  une tendance haussière tient tant que le prix ne CLÔTURE pas sous le plus bas du
  dernier pullback (protected low). Compte des cassures (BOS) = fraîcheur (Wysetrade).
- liquidity_pools : PDH/PDL (jour Forex clos à 17:00 New York), range Asie, plus haut /
  plus bas du jour, equal highs/lows, swings M15 (ICT : BSL au-dessus, SSL en dessous).
- candle_trigger : déclencheurs objectifs 38,2 %, engulfing, close above/below.
- fvgs : Fair Value Gaps créées par un displacement.
- killzone / news_blackout : le temps fait partie du setup (ICT).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import indicators as ind

NY = ZoneInfo("America/New_York")


# ------------------------------------------------------------------ structure
@dataclass
class StructureState:
    trend: str             # up | down | none
    protected: float | None  # niveau dont la clôture au-delà invalide la tendance
    bos_count: int         # cassures dans le sens depuis le dernier changement (fraîcheur)
    last_high: float | None
    last_low: float | None


def structure_trend(df: pd.DataFrame, left: int = 2, right: int = 2) -> StructureState:
    """Rejoue les bougies une à une ; un swing n'est connu que `right` bougies après lui."""
    h, l, c = df["h"].to_numpy(), df["l"].to_numpy(), df["c"].to_numpy()
    n = len(df)
    state, protected, bos = "none", None, 0
    sh = sl = None                     # dernier swing high / low confirmé et non consommé
    sh_used = sl_used = True
    for i in range(n):
        j = i - right                  # swing confirmé à l'instant i
        if j >= left:
            win_h, win_l = h[j - left:j + right + 1], l[j - left:j + right + 1]
            if h[j] == win_h.max() and h[j] > h[j - left:j].max():
                sh, sh_used = float(h[j]), False
            if l[j] == win_l.min() and l[j] < l[j - left:j].min():
                sl, sl_used = float(l[j]), False
        if sh is not None and not sh_used and c[i] > sh:          # clôture au-dessus d'un swing high
            sh_used = True
            if state == "up":
                bos += 1
            else:
                state, bos = "up", 1
            protected = sl if sl is not None else float(l[max(0, i - 5):i + 1].min())
        elif sl is not None and not sl_used and c[i] < sl:        # clôture sous un swing low
            sl_used = True
            if state == "down":
                bos += 1
            else:
                state, bos = "down", 1
            protected = sh if sh is not None else float(h[max(0, i - 5):i + 1].max())
        if state == "up" and protected is not None and c[i] < protected:
            state, bos, protected = "down", 1, sh
        elif state == "down" and protected is not None and c[i] > protected:
            state, bos, protected = "up", 1, sl
    return StructureState(state, protected, bos, sh, sl)


# ------------------------------------------------------------------ bougies
def candle_trigger(bar: pd.Series, prev: pd.Series, d: int) -> str | None:
    """Déclencheurs objectifs (vidéo « technical analysis ») dans le sens d (+1 achat, -1 vente)."""
    o, h, l, c = bar["o"], bar["h"], bar["l"], bar["c"]
    rng = h - l
    if rng <= 0:
        return None
    body_prev = abs(prev["c"] - prev["o"])
    # engulfing : changement de couleur + corps plus grand que le précédent
    if d * (c - o) > 0 and d * (prev["c"] - prev["o"]) < 0 and abs(c - o) > body_prev:
        return "engulfing"
    # close above / below : clôture au-delà de l'extrême de la bougie précédente
    if d == 1 and c > prev["h"]:
        return "close_above"
    if d == -1 and c < prev["l"]:
        return "close_below"
    # 38,2 % : tout le corps au-dessus du retracement 38,2 % (achat) ou en dessous (vente)
    if d == 1 and min(o, c) >= h - 0.382 * rng:
        return "candle_38.2"
    if d == -1 and max(o, c) <= l + 0.382 * rng:
        return "candle_38.2"
    return None


def displacement_bar(bar: pd.Series, atr: float, d: int, mult: float = 1.0, close_pos_min: float = 0.7) -> bool:
    """Bougie de déplacement : grand corps dans le sens, clôture près de l'extrême."""
    body = d * (bar["c"] - bar["o"])
    rng = bar["h"] - bar["l"]
    close_pos = (bar["c"] - bar["l"]) / rng if rng > 0 else 0.5
    return body >= mult * atr and (close_pos >= close_pos_min if d == 1 else close_pos <= 1 - close_pos_min)


def fvgs(df: pd.DataFrame, start: int, d: int, min_size: float = 0.0) -> list[tuple[int, float, float]]:
    """FVG formées à partir de l'indice `start` : (indice de la 3e bougie, bas, haut) de la zone."""
    h, l = df["h"].to_numpy(), df["l"].to_numpy()
    out = []
    for k in range(max(start, 2), len(df)):
        if d == 1 and h[k - 2] < l[k] and l[k] - h[k - 2] >= min_size:
            out.append((k, float(h[k - 2]), float(l[k])))
        if d == -1 and l[k - 2] > h[k] and l[k - 2] - h[k] >= min_size:
            out.append((k, float(h[k]), float(l[k - 2])))
    return out


def impulse_leg(df: pd.DataFrame, lookback: int, d: int) -> tuple[float, float, int]:
    """Dernière jambe dans le sens d : (départ, extrême, indice de l'extrême)."""
    win = df.iloc[-lookback:]
    if d == 1:
        k = int(np.argmax(win["h"].to_numpy()))
        top = float(win["h"].iloc[k])
        start = float(win["l"].iloc[:k + 1].min()) if k > 0 else float(win["l"].iloc[0])
        return start, top, len(df) - lookback + k
    k = int(np.argmin(win["l"].to_numpy()))
    bottom = float(win["l"].iloc[k])
    start = float(win["h"].iloc[:k + 1].max()) if k > 0 else float(win["h"].iloc[0])
    return start, bottom, len(df) - lookback + k


# ------------------------------------------------------------------ liquidité
def forex_day(ts: pd.Timestamp) -> date:
    """Jour de trading Forex : clôture à 17:00 New York (DST gérée)."""
    return (ts.tz_convert(NY) + pd.Timedelta(hours=7)).date()


def liquidity_pools(h1: pd.DataFrame, m15: pd.DataFrame, now: datetime, atr_m15: float,
                    asia_utc: tuple[int, int] = (0, 7), equal_tol_atr: float = 0.1) -> list[dict]:
    pools: list[dict] = []
    days = pd.Series([forex_day(t) for t in h1.index], index=h1.index)
    today = forex_day(pd.Timestamp(now))
    prev_days = sorted({d for d in days if d < today})
    if prev_days:
        pd_bars = h1[days == prev_days[-1]]
        pools += [{"name": "PDH", "price": float(pd_bars["h"].max()), "side": "BSL", "kind": "external"},
                  {"name": "PDL", "price": float(pd_bars["l"].min()), "side": "SSL", "kind": "external"}]
    today_bars = m15[[forex_day(t) == today for t in m15.index]]
    if len(today_bars):
        pools += [{"name": "haut du jour", "price": float(today_bars["h"].max()), "side": "BSL", "kind": "internal"},
                  {"name": "bas du jour", "price": float(today_bars["l"].min()), "side": "SSL", "kind": "internal"}]
    a0, a1 = asia_utc
    if pd.Timestamp(now).hour >= a1:
        d0 = pd.Timestamp(now).normalize()
        asia = m15[(m15.index >= d0 + pd.Timedelta(hours=a0)) & (m15.index < d0 + pd.Timedelta(hours=a1))]
        if len(asia) >= 8:
            pools += [{"name": "haut Asie", "price": float(asia["h"].max()), "side": "BSL", "kind": "external"},
                      {"name": "bas Asie", "price": float(asia["l"].min()), "side": "SSL", "kind": "external"}]
    highs, lows = ind.swings(m15.iloc[-96:])
    tol = equal_tol_atr * atr_m15
    for side, pts, name in (("BSL", highs, "equal highs"), ("SSL", lows, "equal lows")):
        prices = [p for _, p in pts]
        for i in range(len(prices)):
            for j in range(i + 1, len(prices)):
                if abs(prices[i] - prices[j]) <= tol:
                    lvl = max(prices[i], prices[j]) if side == "BSL" else min(prices[i], prices[j])
                    pools.append({"name": name, "price": float(lvl), "side": side, "kind": "external"})
        for _, p in pts[-6:]:
            pools.append({"name": "swing M15", "price": float(p), "side": side, "kind": "internal"})
    # dédoublonnage (niveaux quasi identiques : on garde le plus significatif)
    rank = {"PDH": 0, "PDL": 0, "haut Asie": 1, "bas Asie": 1, "equal highs": 2, "equal lows": 2,
            "haut du jour": 3, "bas du jour": 3, "swing M15": 4}
    pools.sort(key=lambda p: rank.get(p["name"], 9))
    kept: list[dict] = []
    for p in pools:
        if all(abs(p["price"] - k["price"]) > tol or p["side"] != k["side"] for k in kept):
            kept.append(p)
    return kept


# ------------------------------------------------------------------ temps
def ny_hour(ts: datetime) -> float:
    t = pd.Timestamp(ts).tz_convert(NY)
    return t.hour + t.minute / 60


def killzone(ts: datetime, zones: dict[str, list[float]]) -> str | None:
    """Killzones exprimées en heure de New York (DST automatique)."""
    h = ny_hour(ts)
    for name, (a, b) in zones.items():
        if a <= h < b:
            return name
    return None


def first_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def news_blackout(now: datetime, symbol: str, cfg: dict) -> tuple[bool, str]:
    """Pas de nouvelle position autour des annonces majeures (ICT, NNFX)."""
    n = cfg.get("news", {})
    before = timedelta(minutes=n.get("blackout_minutes_before", 30))
    after = timedelta(minutes=n.get("blackout_minutes_after", 30))
    events = []
    if n.get("auto_nfp", True):
        ff = first_friday(now.year, now.month)
        t = datetime(ff.year, ff.month, ff.day, 8, 30, tzinfo=NY).astimezone(timezone.utc)
        events.append({"time": t, "name": "NFP", "currencies": ["USD"]})
    for e in n.get("events", []) or []:
        t = pd.Timestamp(e["time"])
        t = (t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")).to_pydatetime()
        events.append({"time": t, "name": e.get("name", "annonce"), "currencies": e.get("currencies", [])})
    for e in events:
        if e["currencies"] and not any(c in symbol for c in e["currencies"]):
            continue
        if e["time"] - before <= now <= e["time"] + after:
            return True, f"annonce {e['name']} à {e['time']:%H:%M} UTC : pas de nouvelle position"
    return False, ""
