"""BreakRetest_v2 — ancienne résistance cassée devenue support (et inverse).

Sources : vidéo « technical analysis » (break and retest en tendance, zone et non ligne,
stop au-delà du niveau, cible au prochain niveau), The Trading Channel, Wysetrade
(pullback vers résistance devenue support, bougie de rejet puis confirmation).
"""
from __future__ import annotations

from ..analysis import indicators as ind
from ..analysis import structure as st
from ..analysis.market import MarketContext
from .base import build_setup, buffer, opposite_impulse, params, sign_of, sp

NAME = "BreakRetest_v2"
ESSENTIAL = ["context", "break", "retest", "trigger"]


def scan(ctx: MarketContext, direction: str, cfg: dict):
    d = sign_of(direction)
    m15, m5 = ctx.frames["M15"], ctx.frames["M5"]
    atr = ctx.atr_m5
    highs, lows = ind.swings(m15.iloc[-int(sp(cfg, "br_level_lookback_m15")):])
    levels = [p for _, p in (highs if d == 1 else lows)][::-1]   # le plus récent d'abord
    recent = m5.iloc[-13:]                                       # ~1 h de M5
    closes = recent["c"].to_numpy()
    zone = sp(cfg, "br_zone_atr") * atr                          # le niveau est une ZONE
    hold = int(sp(cfg, "br_hold_bars"))

    for level in levels:
        brk = next((i for i in range(len(recent) - 1) if d * (closes[i] - level) >= sp(cfg, "br_break_min_atr") * atr),
                   None)
        if brk is None:
            continue
        before = m5["c"].iloc[-(13 - brk) - hold:-(13 - brk)]
        if len(before) < hold or not (d * (before - level) < 0).all():
            continue                                             # le niveau n'avait pas tenu avant
        after = recent.iloc[brk + 1:]
        if after.empty:
            continue
        back = after["l"] if d == 1 else after["h"]
        touches = d * (back - level) <= zone
        held = (d * (after["c"] - level) >= -sp(cfg, "br_fall_through_atr") * atr).all()   # pas de clôture franche de l'autre côté
        last, prev = m5.iloc[-1], m5.iloc[-2]
        trigger = st.candle_trigger(last, prev, d)
        brk_bar = recent.iloc[brk]
        conf = {
            "context": ctx.regime == ("TREND_UP" if d == 1 else "TREND_DOWN"),
            "break": st.displacement_bar(brk_bar, atr, d, sp(cfg, "br_break_displacement"),
                                         sp(cfg, "displacement_close_pos"))
                     or d * (brk_bar["c"] - level) >= sp(cfg, "br_strong_break_atr") * atr,
            "retest": bool(touches.any() and held),
            "trigger": trigger is not None and d * (last["c"] - level) > 0 and bool(touches.iloc[-2:].any()),
            "fresh_trend": ctx.m15.fresh,
            "no_opposite_impulse": not opposite_impulse(after, atr, d, sp(cfg, "opposite_displacement_atr"),
                                                        lookback=len(after)),
            "structure": ctx.m15.struct_trend == ("up" if d == 1 else "down"),
            "killzone": ctx.killzone is not None,
        }
        extreme = float(back.min()) if d == 1 else float(back.max())
        stop = min(extreme, level - zone) - buffer(ctx, cfg) if d == 1 else max(extreme, level + zone) + buffer(ctx, cfg)
        meta = {"level": round(level, 6), "trigger": trigger, "price_zone": ctx.zone(float(last["c"]))}
        notes = [f"niveau {level:.5f} cassé puis retesté", f"déclencheur {trigger or 'absent'}"]
        return build_setup(ctx, NAME, direction, float(last["c"]), float(stop), conf, ESSENTIAL, notes, cfg, meta)
    return None
