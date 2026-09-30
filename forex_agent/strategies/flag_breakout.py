"""FlagBreakout_v1 — cassure d'un drapeau dans une tendance volatile.

Source : vidéo « The only technical analysis video » : impulsion (mât), courte
consolidation (drapeau), bougie de cassure ; UNIQUEMENT quand le prix reste au-dessus
(au-dessous) de l'EMA20 = tendance volatile ; stop sous le plus bas du drapeau + ATR ;
cible au niveau de résistance précédent. Wysetrade : pattern de continuation dans le
sens de la tendance supérieure.
"""
from __future__ import annotations

from ..analysis.market import MarketContext
from .base import build_setup, buffer, params, sign_of, sp

NAME = "FlagBreakout_v1"
ESSENTIAL = ["context", "pole", "flag", "volatile_trend", "breakout"]


def scan(ctx: MarketContext, direction: str, cfg: dict):
    d = sign_of(direction)
    m5 = ctx.frames["M5"]
    atr = ctx.atr_m5
    last = m5.iloc[-1]
    pole_min = sp(cfg, "flag_pole_atr") * atr
    for f in range(3, 9):
        flag = m5.iloc[-1 - f:-1]
        pre = m5.iloc[-1 - f - 8:-1 - f]
        if len(pre) < 8:
            return None
        if d == 1:
            top = max(pre["h"].max(), flag["h"].iloc[0])
            bottom = pre["l"].iloc[:int(pre["h"].to_numpy().argmax()) + 1].min()
            fl_hi, fl_lo = flag["h"].max(), flag["l"].min()
        else:
            top = min(pre["l"].min(), flag["l"].iloc[0])
            bottom = pre["h"].iloc[:int(pre["l"].to_numpy().argmin()) + 1].max()
            fl_hi, fl_lo = flag["l"].min(), flag["h"].max()     # « haut » = bord de cassure
        pole = d * (top - bottom)
        if pole < pole_min:
            continue
        flag_range = abs(flag["h"].max() - flag["l"].min())
        shallow = d * (fl_lo - (top - d * sp(cfg, "flag_max_retrace") * pole)) >= 0   # correction max du drapeau
        if flag_range > sp(cfg, "flag_max_range_ratio") * pole or not shallow:
            continue
        seg = m5.iloc[-1 - f - 8:]
        above_ema = bool((d * (seg["c"] - seg["ema20"]) >= -sp(cfg, "flag_ema_tol_atr") * atr).all())
        breakout = d * (last["c"] - fl_hi) > 0 and d * (last["c"] - last["o"]) >= sp(cfg, "flag_break_body_atr") * atr
        conf = {
            "context": ctx.regime == ("TREND_UP" if d == 1 else "TREND_DOWN"),
            "pole": True,
            "flag": True,
            "volatile_trend": above_ema,
            "breakout": bool(breakout),
            "fresh_trend": ctx.m15.fresh,
            "strong_trend": ctx.trend_strength == "strong",
            "killzone": ctx.killzone is not None,
        }
        stop = fl_lo - d * buffer(ctx, cfg)
        meta = {"pole_atr": round(pole / atr, 1), "flag_bars": f}
        notes = [f"mât {pole / atr:.1f} ATR, drapeau {f} bougies", "cassure" if breakout else "pas encore de cassure"]
        projection = float(last["c"]) + d * pole
        return build_setup(ctx, NAME, direction, float(last["c"]), float(stop), conf, ESSENTIAL, notes, cfg, meta,
                           extra_levels=[(projection, "projection du mât")])
    return None
