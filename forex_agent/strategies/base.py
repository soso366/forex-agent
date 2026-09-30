"""Socle commun des stratégies.

Principes tirés des sources :
- ENTRÉE BINAIRE (NNFX) : toutes les conditions essentielles sont vraies, sinon NO TRADE.
  Les confirmations optionnelles sont journalisées ; leur poids sera fixé par les
  statistiques, jamais par des pondérations arbitraires (synthèse TTC/Wysetrade).
- STOP à l'invalidation logique + tampon ATR ; la taille s'adapte au stop (ICT, TA video).
- CIBLE = premier niveau de liquidité / structure opposé, choisi AVANT l'entrée, pas pour
  « un joli ratio » (ICT) ; ne jamais viser au-delà d'un niveau majeur (TA video).
Une stratégie ne décide jamais de la taille : c'est le Risk Manager.
"""
from __future__ import annotations

import pandas as pd

from .. import fx
from ..analysis.market import MarketContext
from ..config import Setup

GLOBAL_ESSENTIALS = ("rr", "spread", "news")


def sign_of(direction: str) -> int:
    return 1 if direction == "BUY" else -1


STRATEGY_DEFAULTS = {
    # communs
    "stop_buffer_atr": 0.5, "target_offset_atr": 0.05, "target_min_spreads": 2.0,
    "opposite_displacement_atr": 1.5, "displacement_atr": 1.0, "displacement_close_pos": 0.7,
    # TrendPullback
    "min_pullback_pct": 0.30, "max_pullback_pct": 0.786, "tp_min_leg_atr": 2.0, "tp_leg_lookback": 30,
    "tp_value_zone_atr": 0.3,
    # BreakRetest
    "br_level_lookback_m15": 48, "br_break_min_atr": 0.1, "br_hold_bars": 6, "br_zone_atr": 0.25,
    "br_fall_through_atr": 0.1, "br_strong_break_atr": 0.3, "br_break_displacement": 0.6,
    # FlagBreakout
    "flag_pole_atr": 2.5, "flag_max_range_ratio": 0.5, "flag_max_retrace": 0.5, "flag_ema_tol_atr": 0.2,
    "flag_break_body_atr": 0.5,
    # DoubleTopBottom
    "dt_retest_atr": 0.25, "dt_min_separation": 4,
    # SweepMSS
    "sweep_beyond_atr": 0.05, "sweep_lookback": 8, "sweep_clean_bars": 12, "fvg_min_atr": 0.0,
    "fvg_entry_tol_atr": 0.1,
    # RangeFade
    "rf_edge_pct": 0.15, "rf_wick_pct": 0.5,
}


def params(cfg: dict) -> dict:
    return cfg.get("strategy_params", {})


def sp(cfg: dict, key: str):
    """Paramètre de stratégie : config « strategy_params: », sinon valeur par défaut documentée."""
    return params(cfg).get(key, STRATEGY_DEFAULTS[key])


def buffer(ctx: MarketContext, cfg: dict) -> float:
    """Tampon au-delà de l'invalidation : fraction d'ATR M5 + demi-spread."""
    return sp(cfg, "stop_buffer_atr") * ctx.atr_m5 + (ctx.ask - ctx.bid) / 2


def opposite_impulse(m5: pd.DataFrame, atr: float, d: int, mult: float, lookback: int = 6) -> bool:
    """« D'où vient le prix » (Wysetrade) : une forte impulsion contraire récente disqualifie le setup."""
    win = m5.iloc[-lookback:]
    return bool((d * (win["c"] - win["o"]) <= -mult * atr).any())


def build_setup(ctx: MarketContext, strategy: str, direction: str, entry: float, stop: float,
                conf: dict[str, bool], essential: list[str], notes: list[str], cfg: dict,
                meta: dict | None = None, target: float | None = None, fallback_rr: float = 2.0,
                extra_levels: list[tuple[float, str]] | None = None) -> Setup | None:
    d = sign_of(direction)
    risk = d * (entry - stop)
    if risk <= 0:
        return None
    meta = dict(meta or {})
    spread = ctx.ask - ctx.bid
    if target is None:
        levels = ctx.levels_beyond(entry, d) + [lv for lv in (extra_levels or []) if d * (lv[0] - entry) > 0]
        min_gap = sp(cfg, "target_min_spreads") * spread
        levels = sorted((lv for lv in levels if d * (lv[0] - entry) > min_gap), key=lambda x: d * (x[0] - entry))
        if levels:
            lvl, name = levels[0]
            target = lvl - d * (spread + sp(cfg, "target_offset_atr") * ctx.atr_m5)   # sortir juste avant le niveau
            meta.setdefault("target_level", name)
        else:
            target = entry + d * fallback_rr * risk
            meta.setdefault("target_level", f"espace libre ({fallback_rr}R)")
    min_rr = cfg["risk"].get("min_rr", 1.5)
    reward = d * (target - entry)
    net_rr = (reward - spread) / (risk + spread) if reward > 0 else 0.0
    conf = dict(conf)
    conf["rr"] = net_rr >= min_rr
    conf["spread"] = spread <= cfg["risk"].get("max_spread_to_stop_ratio", 0.25) * risk
    conf["news"] = not ctx.news_block
    notes.append(f"R:R net de spread {net_rr:.2f} vers {meta.get('target_level')}")
    dec = 3 if fx.pip_size(ctx.symbol) == 0.01 else 5
    ess = list(dict.fromkeys(list(essential) + list(GLOBAL_ESSENTIALS)))
    return Setup(symbol=ctx.symbol, direction=direction, strategy=strategy,
                 entry=round(float(entry), dec), stop=round(float(stop), dec), target=round(float(target), dec),
                 confirmations={k: bool(v) for k, v in conf.items()}, notes=notes,
                 essential=ess, meta=meta)


def qualifies(setup: Setup, trading_cfg: dict) -> tuple[bool, str]:
    missing = [k for k in setup.essential if not setup.confirmations.get(k)]
    if missing:
        return False, f"conditions essentielles manquantes : {', '.join(missing)}"
    optional = [k for k in setup.confirmations if k not in setup.essential]
    ok_opt = [k for k in optional if setup.confirmations[k]]
    need = trading_cfg.get("min_optional_confirmations", 0)
    if len(ok_opt) < need:
        return False, f"{len(ok_opt)} confirmations optionnelles (min {need})"
    return True, f"toutes les conditions essentielles réunies (+{len(ok_opt)}/{len(optional)} optionnelles)"
