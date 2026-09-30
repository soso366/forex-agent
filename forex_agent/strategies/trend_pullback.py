"""TrendPullback_v2 — continuation de tendance sur pullback propre.

Sources : Wysetrade (tendance fraîche, pullback 25–50 %+, « d'où vient le prix »),
The Trading Channel / synthèse TTC (HTF = biais, LTF = déclencheur, pullback vers zone de valeur),
vidéo « technical analysis » (EMA20/50 zone de valeur, bougies objectives, cible = ancien plus haut),
Trading Rush (MACD en confirmation de momentum uniquement).
"""
from __future__ import annotations

from ..analysis import indicators as ind
from ..analysis import structure as st
from ..analysis.market import MarketContext
from .base import build_setup, buffer, opposite_impulse, params, sign_of, sp

NAME = "TrendPullback_v2"
ESSENTIAL = ["context", "fresh_trend", "pullback", "location", "trigger"]


def scan(ctx: MarketContext, direction: str, cfg: dict):
    d = sign_of(direction)
    p = params(cfg)
    m5, m1 = ctx.frames["M5"], ctx.frames["M1"]
    atr = ctx.atr_m5
    start, extreme, k = st.impulse_leg(m5, int(sp(cfg, "tp_leg_lookback")), d)
    n = len(m5)
    if k > n - 3 or k < n - 20:
        return None                                   # pas de jambe puis pullback récents
    leg = d * (extreme - start)
    if leg < sp(cfg, "tp_min_leg_atr") * atr:
        return None                                   # pas d'impulsion digne de ce nom
    pb = m5.iloc[k + 1:]
    pb_extreme = float(pb["l"].min()) if d == 1 else float(pb["h"].max())
    retr = d * (extreme - pb_extreme) / leg
    last, prev = m5.iloc[-1], m5.iloc[-2]

    # zone de valeur : EMA20/EMA50 M5 ou ancien niveau cassé (résistance devenue support)
    zone_hits = []
    vz = sp(cfg, "tp_value_zone_atr") * atr
    for lvl, name in ((float(pb["ema20"].iloc[-1]), "EMA20"), (float(pb["ema50"].iloc[-1]), "EMA50")):
        if abs(pb_extreme - lvl) <= vz:
            zone_hits.append(name)
    for lvl, name in ctx.levels_beyond(pb_extreme + d * vz, -d)[:3]:
        if abs(pb_extreme - lvl) <= vz:
            zone_hits.append(f"ancien niveau ({name})")
    extreme_recent = (pb["l"].idxmin() if d == 1 else pb["h"].idxmax()) in m5.index[-3:]
    trigger = st.candle_trigger(last, prev, d)
    leg_bodies = (m5["c"] - m5["o"]).abs().iloc[max(0, k - 5):k + 1].mean()
    pb_bodies = (pb["c"] - pb["o"]).abs().iloc[:-1].mean() if len(pb) > 1 else leg_bodies
    macd = ind.macd_hist(m5["c"]).iloc[-1]

    want_trend = "up" if d == 1 else "down"
    conf = {
        "context": ctx.regime == ("TREND_UP" if d == 1 else "TREND_DOWN")
                   and ctx.m15.struct_trend == want_trend and ctx.h1.struct_trend != ("down" if d == 1 else "up"),
        "fresh_trend": ctx.m15.fresh,
        "pullback": sp(cfg, "min_pullback_pct") <= retr <= sp(cfg, "max_pullback_pct")
                    and not opposite_impulse(pb, atr, d, sp(cfg, "opposite_displacement_atr"), lookback=len(pb)),
        "location": bool(zone_hits),
        "trigger": trigger is not None and extreme_recent,
        # optionnelles (journalisées, pondérées plus tard par les stats)
        "deep_pullback": retr >= 0.5,
        "momentum_loss_in_pullback": pb_bodies < leg_bodies,
        "m1_confirm": d * (m1["c"].iloc[-1] - m1["ema9"].iloc[-1]) > 0,
        "rsi_reset": (pb["rsi"].min() < 50 if d == 1 else pb["rsi"].max() > 50) and d * (last["rsi"] - 50) > 0,
        "macd_aligned": d * macd > 0,
        "killzone": ctx.killzone is not None,
    }
    stop = pb_extreme - d * buffer(ctx, cfg)
    meta = {"leg_retracement": round(retr, 2), "value_zone": zone_hits, "trigger": trigger,
            "price_zone": ctx.zone(float(last["c"]))}
    notes = [f"pullback {retr:.0%} de la jambe vers {', '.join(zone_hits) or 'aucune zone'}",
             f"déclencheur {trigger or 'absent'}"]
    return build_setup(ctx, NAME, direction, float(last["c"]), float(stop), conf, ESSENTIAL, notes, cfg, meta,
                       extra_levels=[(extreme, "plus haut de la jambe" if d == 1 else "plus bas de la jambe")])
