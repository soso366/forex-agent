"""RangeFade_v2 — rejet d'une borne de range propre vers le milieu (EXPÉRIMENTALE, paper).

Sources : Wysetrade (range = trader les deux sens ; mèches longues à un niveau clé ;
changement de couleur et bougies qui rétrécissent = perte de momentum), ICT (journée de
consolidation : objectifs plus proches, moins d'agressivité), synthèse TTC (RSI jamais seul).
"""
from __future__ import annotations

from ..analysis import structure as st
from ..analysis.market import MarketContext
from .base import build_setup, buffer, sign_of

NAME = "RangeFade_v2"
ESSENTIAL = ["context", "location", "rejection", "trigger"]


def scan(ctx: MarketContext, direction: str, cfg: dict):
    d = sign_of(direction)
    m5 = ctx.frames["M5"]
    last, prev = m5.iloc[-1], m5.iloc[-2]
    rh, rl = ctx.range_high, ctx.range_low
    w = rh - rl
    if w <= 0:
        return None
    edge = rl if d == 1 else rh
    probe = m5.iloc[-3:]
    reach = probe["l"].min() if d == 1 else probe["h"].max()
    at_edge = d * (reach - edge) <= 0.15 * w
    if not at_edge:
        return None
    # rejet : mèche longue vers la borne sur l'une des 3 dernières bougies
    wicks = [(min(b["o"], b["c"]) - b["l"]) if d == 1 else (b["h"] - max(b["o"], b["c"])) for _, b in probe.iterrows()]
    ranges = [(b["h"] - b["l"]) for _, b in probe.iterrows()]
    rejection = any(r > 0 and wk >= 0.5 * r for wk, r in zip(wicks, ranges))
    approach = m5.iloc[-7:-1]
    bodies = (approach["c"] - approach["o"]).abs().to_numpy()
    trigger = st.candle_trigger(last, prev, d)
    conf = {
        "context": ctx.regime == "RANGE",
        "location": bool(at_edge) and d * (float(last["c"]) - (rl + rh) / 2) < 0,
        "rejection": rejection,
        "trigger": trigger is not None,
        "shrinking_candles": len(bodies) >= 3 and bodies[-1] < bodies[0],
        "rsi_extreme": (m5["rsi"].iloc[-4:].min() < 35) if d == 1 else (m5["rsi"].iloc[-4:].max() > 65),
        "flat_m15": ctx.m15.trend == "flat",
    }
    stop = (min(rl, float(probe["l"].min())) - buffer(ctx, cfg)) if d == 1 else \
           (max(rh, float(probe["h"].max())) + buffer(ctx, cfg))
    meta = {"range": [round(rl, 6), round(rh, 6)], "trigger": trigger}
    notes = [f"borne {'basse' if d == 1 else 'haute'} du range M15", f"déclencheur {trigger or 'absent'}"]
    # objectif rapproché (journée de consolidation) : milieu du range, sauf niveau plus proche
    return build_setup(ctx, NAME, direction, float(last["c"]), float(stop), conf, ESSENTIAL, notes, cfg, meta,
                       extra_levels=[((rl + rh) / 2, "milieu du range")])
