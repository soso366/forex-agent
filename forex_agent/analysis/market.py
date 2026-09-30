"""Analyse de marché : transforme les bougies en CONTEXTE. C'est la première étape :
MARCHÉ → RÉGIME → CONTEXTE MULTI-TIMEFRAME → LIQUIDITÉ → (seulement ensuite) STRATÉGIE.

Hiérarchie (sources : NNFX/TTC/Wysetrade, ICT) :
- H1 = biais / destination, M15 = structure et zone, M5 = setup, M1 = exécution.
- Tendance définie objectivement par la structure (protected low/high) ET les EMA.
- Liquidité nommée (PDH/PDL, Asie, equal highs/lows, swings) et dealing range 24 h.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from .. import fx
from . import indicators as ind
from . import structure as st


@dataclass
class TFView:
    trend: str            # tendance EMA : up | down | flat
    structure: str        # HH_HL | LH_LL | mixed (deux derniers swings)
    struct_trend: str     # tendance structurelle : up | down | none
    protected: float | None
    bos_count: int        # nombre de cassures depuis le changement de structure
    extension_atr: float  # |clôture - EMA20| / ATR : tendance étendue ou non
    ema20: float
    ema50: float
    atr: float
    fresh_max_bos: int = 3          # regime.fresh_max_bos
    fresh_max_ext_atr: float = 2.5  # regime.fresh_max_ext_atr

    @property
    def fresh(self) -> bool:
        return self.bos_count <= self.fresh_max_bos and self.extension_atr <= self.fresh_max_ext_atr


@dataclass
class MarketContext:
    symbol: str
    time: datetime
    bid: float
    ask: float
    spread_pips: float
    session: str
    killzone: str | None
    h1: TFView
    m15: TFView
    er_m15: float
    trend_strength: str   # strong | normal | weak
    atr_m5: float
    atr_m5_pips: float
    vol_ratio: float
    volatility: str       # dead | low | normal | high | extreme
    supports: list[float]
    resistances: list[float]
    pools: list[dict]
    dealing_high: float
    dealing_low: float
    range_high: float
    range_low: float
    range_width_atr: float
    range_touches: tuple[int, int]
    regime: str           # TREND_UP | TREND_DOWN | RANGE | CHOP | DEAD | VOLATILE
    regime_reason: str
    news_block: str = ""
    frames: dict[str, pd.DataFrame] = field(default_factory=dict, repr=False)

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def equilibrium(self) -> float:
        return (self.dealing_high + self.dealing_low) / 2

    def zone(self, price: float) -> str:
        """Premium / discount dans le dealing range 24 h (M15)."""
        return "premium" if price > self.equilibrium else "discount"

    def levels_beyond(self, price: float, d: int) -> list[tuple[float, str]]:
        """Niveaux opposés (liquidité + S/R) au-delà de `price` dans le sens d, du plus proche au plus loin."""
        pts = [(p["price"], p["name"]) for p in self.pools if d * (p["price"] - price) > 0]
        pts += [(r, "résistance M15") for r in self.resistances if d == 1 and r > price]
        pts += [(s, "support M15") for s in self.supports if d == -1 and s < price]
        return sorted(pts, key=lambda x: d * (x[0] - price))

    def nearest_resistance(self, price: float) -> float | None:
        lv = self.levels_beyond(price, 1)
        return lv[0][0] if lv else None

    def nearest_support(self, price: float) -> float | None:
        lv = self.levels_beyond(price, -1)
        return lv[0][0] if lv else None

    def summary(self) -> dict:
        d = 3 if fx.pip_size(self.symbol) == 0.01 else 5
        return {
            "symbol": self.symbol, "bid": self.bid, "ask": self.ask,
            "spread_pips": round(self.spread_pips, 2), "session": self.session, "killzone": self.killzone,
            "regime": self.regime, "regime_reason": self.regime_reason, "trend_strength": self.trend_strength,
            "trend_ema": {"H1": self.h1.trend, "M15": self.m15.trend},
            "trend_structure": {"H1": self.h1.struct_trend, "M15": self.m15.struct_trend},
            "protected_level": {"H1": _r(self.h1.protected, d), "M15": _r(self.m15.protected, d)},
            "fresh_trend": {"H1": self.h1.fresh, "M15": self.m15.fresh},
            "structure": {"H1": self.h1.structure, "M15": self.m15.structure},
            "efficiency_m15": round(self.er_m15, 2),
            "volatility": self.volatility, "atr_m5_pips": round(self.atr_m5_pips, 2),
            "vol_ratio": round(self.vol_ratio, 2),
            "dealing_range_24h": {"high": _r(self.dealing_high, d), "low": _r(self.dealing_low, d),
                                  "price_zone": self.zone(self.mid)},
            "liquidity": [{**p, "price": round(p["price"], d)} for p in self.pools],
            "news": self.news_block or None,
        }


def _r(x, d):
    return round(x, d) if x is not None else None


def session_of(ts: datetime) -> str:
    h = ts.hour
    if 12 <= h < 16:
        return "overlap_london_ny"
    if 7 <= h < 12:
        return "london"
    if 16 <= h < 21:
        return "new_york"
    return "asia"


REGIME_DEFAULTS = {
    "vol_extreme_ratio": 2.5,    # ATR M5 / médiane > x -> VOLATILE
    "vol_high_ratio": 1.5,
    "vol_low_ratio": 0.7,
    "dead_atr_spread_mult": 1.2,  # ATR M5 < x * spread -> DEAD
    "er_trend_min": 0.30,         # efficiency ratio M15 minimal pour une tendance
    "er_range_max": 0.25,
    "er_strong": 0.5,
    "range_width_atr_min": 3.0,
    "range_width_atr_max": 15.0,
    "range_touches_min": 2,
    "range_touch_band": 0.15,
    "fresh_max_bos": 3,
    "fresh_max_ext_atr": 2.5,
    "equal_level_tol_atr": 0.1,
}


def rp(cfg: dict | None, key: str):
    """Paramètre de régime (config « regime: »), valeur par défaut documentée ci-dessus."""
    return ((cfg or {}).get("regime") or {}).get(key, REGIME_DEFAULTS[key])


def classify(v_h1: "TFView", v_m15: "TFView", er: float, vol_ratio: float, atr_pips: float,
             spread_pips: float, width_atr: float, touch_hi: int, touch_lo: int,
             cfg: dict | None = None) -> tuple[str, str, str, str]:
    """Volatilité, force, régime et raison — séparé d'analyze() pour pouvoir être réévalué (Parameter Lab)."""
    if vol_ratio > rp(cfg, "vol_extreme_ratio"):
        vol = "extreme"
    elif atr_pips < rp(cfg, "dead_atr_spread_mult") * spread_pips:
        vol = "dead"
    elif vol_ratio > rp(cfg, "vol_high_ratio"):
        vol = "high"
    elif vol_ratio < rp(cfg, "vol_low_ratio"):
        vol = "low"
    else:
        vol = "normal"
    er_trend = rp(cfg, "er_trend_min")
    strength = "strong" if er >= rp(cfg, "er_strong") else "normal" if er >= er_trend else "weak"

    def aligned(direction: str) -> bool:
        return (v_h1.trend == v_m15.trend == direction and er >= er_trend
                and v_m15.struct_trend != ("down" if direction == "up" else "up"))

    if vol == "extreme":
        regime, why = "VOLATILE", f"ATR M5 = {vol_ratio:.1f}x sa médiane (spike/news)"
    elif vol == "dead":
        regime, why = "DEAD", f"ATR M5 {atr_pips:.1f} pips trop faible vs spread {spread_pips:.1f}"
    elif aligned("up"):
        regime, why = "TREND_UP", f"H1 et M15 haussiers (structure M15 {v_m15.struct_trend}), efficiency {er:.2f}"
    elif aligned("down"):
        regime, why = "TREND_DOWN", f"H1 et M15 baissiers (structure M15 {v_m15.struct_trend}), efficiency {er:.2f}"
    elif (er < rp(cfg, "er_range_max")
          and rp(cfg, "range_width_atr_min") <= width_atr <= rp(cfg, "range_width_atr_max")
          and touch_hi >= rp(cfg, "range_touches_min") and touch_lo >= rp(cfg, "range_touches_min")
          and not (v_h1.trend == v_m15.trend != "flat")):     # pas de « range » contre une tendance H1+M15
        regime, why = "RANGE", f"range M15 {width_atr:.1f} ATR, bornes touchées {touch_hi}/{touch_lo}"
    else:
        regime = "CHOP"
        why = f"H1 {v_h1.trend} / M15 {v_m15.trend}, efficiency {er:.2f} : pas de biais suffisamment clair"
    return vol, strength, regime, why


def _tf_view(df: pd.DataFrame) -> TFView:
    last = df.iloc[-1]
    slope = df["ema20"].iloc[-1] - df["ema20"].iloc[-6]
    if last["ema20"] > last["ema50"] and slope > 0 and last["c"] > last["ema50"]:
        trend = "up"
    elif last["ema20"] < last["ema50"] and slope < 0 and last["c"] < last["ema50"]:
        trend = "down"
    else:
        trend = "flat"
    highs, lows = ind.swings(df.iloc[-60:])
    structure = "mixed"
    if len(highs) >= 2 and len(lows) >= 2:
        hh, hl = highs[-1][1] > highs[-2][1], lows[-1][1] > lows[-2][1]
        lh, ll = highs[-1][1] < highs[-2][1], lows[-1][1] < lows[-2][1]
        structure = "HH_HL" if hh and hl else "LH_LL" if lh and ll else "mixed"
    s = st.structure_trend(df)
    ext = abs(last["c"] - last["ema20"]) / last["atr"] if last["atr"] > 0 else 0.0
    return TFView(trend, structure, s.trend, s.protected, s.bos_count, float(ext),
                  float(last["ema20"]), float(last["ema50"]), float(last["atr"]))


MIN_BARS = {"H1": 60, "M15": 60, "M5": 60, "M1": 20}


def analyze(symbol: str, raw: dict[str, pd.DataFrame], bid: float, ask: float,
            now: datetime, cfg: dict | None = None) -> MarketContext:
    cfg = cfg or {}
    for tf, n in MIN_BARS.items():
        if tf in raw and len(raw[tf]) < n:
            raise ValueError(f"{symbol} {tf}: seulement {len(raw[tf])} bougies (min {n})")
    frames = {tf: ind.add_basics(ind.to_mid(df)) for tf, df in raw.items()}
    h1, m15, m5 = frames["H1"], frames["M15"], frames["M5"]
    pip = fx.pip_size(symbol)
    spread_pips = (ask - bid) / pip

    v_h1, v_m15 = _tf_view(h1), _tf_view(m15)
    er = ind.efficiency_ratio(m15["c"], 20)

    for v in (v_h1, v_m15):
        v.fresh_max_bos, v.fresh_max_ext_atr = rp(cfg, "fresh_max_bos"), rp(cfg, "fresh_max_ext_atr")

    atr_m5 = float(m5["atr"].iloc[-1])
    med = float(m5["atr"].iloc[-100:].median())
    vol_ratio = atr_m5 / med if med > 0 else 1.0
    atr_pips = atr_m5 / pip

    sh, sl = ind.swings(m15.iloc[-96:])
    price = (bid + ask) / 2
    resistances = sorted({round(p, 6) for _, p in sh if p > price})
    supports = sorted({round(p, 6) for _, p in sl if p < price})
    asia = tuple(cfg.get("sessions", {}).get("asia_utc", (0, 7)))
    pools = st.liquidity_pools(h1, m15, now, v_m15.atr, asia, rp(cfg, "equal_level_tol_atr"))
    day = m15.iloc[-96:]
    dealing_high, dealing_low = float(day["h"].max()), float(day["l"].min())

    rng = m15.iloc[-32:]
    r_hi, r_lo = float(rng["h"].max()), float(rng["l"].min())
    width = r_hi - r_lo
    width_atr = width / v_m15.atr if v_m15.atr > 0 else 0.0
    band = rp(cfg, "range_touch_band")
    touch_hi = int((rng["h"] >= r_hi - band * width).sum())
    touch_lo = int((rng["l"] <= r_lo + band * width).sum())
    vol, strength, regime, why = classify(v_h1, v_m15, er, vol_ratio, atr_pips, spread_pips,
                                          width_atr, touch_hi, touch_lo, cfg)

    zones = cfg.get("sessions", {}).get("killzones_ny", {"london": [2, 5], "new_york_am": [7, 10]})
    return MarketContext(
        symbol=symbol, time=now, bid=bid, ask=ask, spread_pips=spread_pips,
        session=session_of(now), killzone=st.killzone(now, zones), h1=v_h1, m15=v_m15, er_m15=er,
        trend_strength=strength, atr_m5=atr_m5, atr_m5_pips=atr_pips, vol_ratio=vol_ratio, volatility=vol,
        supports=supports, resistances=resistances, pools=pools,
        dealing_high=dealing_high, dealing_low=dealing_low,
        range_high=r_hi, range_low=r_lo, range_width_atr=width_atr, range_touches=(touch_hi, touch_lo),
        regime=regime, regime_reason=why, frames=frames,
    )
