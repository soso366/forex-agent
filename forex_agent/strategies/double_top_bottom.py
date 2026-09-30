"""DoubleTopBottom_v1 — double bas / double haut avec règles objectives.

Source : vidéo « The only technical analysis video » :
- zone de terminaison du 1er creux = [plus bas du creux, plus bas des corps du creux] ;
- le 2e creux doit TOUCHER la zone ; aucune bougie ne doit CLÔTURER sous la zone ;
- validation = clôture au-dessus de la neckline ; entrée au RETOUR sur la neckline
  avec pression acheteuse (bougie verte) ; stop sous le plus bas du retour ;
- à trader dans le sens de la tendance du timeframe supérieur.
Wysetrade : double bottom + mèche à un support = « trigger event ».
"""
from __future__ import annotations

from ..analysis import indicators as ind
from ..analysis.market import MarketContext
from .base import build_setup, buffer, sign_of

NAME = "DoubleTopBottom_v1"
ESSENTIAL = ["htf_aligned", "second_touch", "neckline_break", "neckline_retest", "buying_pressure"]


def scan(ctx: MarketContext, direction: str, cfg: dict):
    d = sign_of(direction)
    m5 = ctx.frames["M5"]
    atr = ctx.atr_m5
    w = m5.iloc[-60:]
    highs, lows = ind.swings(w, 2, 2)
    pts = lows if d == 1 else highs
    pos = {t: w.index.get_loc(t) for t, _ in pts}
    last = w.iloc[-1]
    for i2 in range(len(pts) - 1, 0, -1):
        for i1 in range(i2 - 1, -1, -1):
            p1, p2 = pos[pts[i1][0]], pos[pts[i2][0]]
            if p2 - p1 < 4:
                continue
            b1 = w.iloc[p1]
            if d == 1:
                zone_far, zone_near = b1["l"], min(b1["o"], b1["c"])
                touch = w["l"].iloc[p2] <= zone_near
                closed_through = (w["c"].iloc[p1:] < zone_far).any()
                neck = float(w["h"].iloc[p1:p2 + 1].max())
            else:
                zone_far, zone_near = b1["h"], max(b1["o"], b1["c"])
                touch = w["h"].iloc[p2] >= zone_near
                closed_through = (w["c"].iloc[p1:] > zone_far).any()
                neck = float(w["l"].iloc[p1:p2 + 1].min())
            if not touch or closed_through:
                continue
            after = w.iloc[p2 + 1:]
            brk = next((k for k in range(len(after)) if d * (after["c"].iloc[k] - neck) > 0), None)
            if brk is None or brk >= len(after) - 1:
                continue
            post = after.iloc[brk + 1:]
            near = (post["l"] <= neck + 0.25 * atr) if d == 1 else (post["h"] >= neck - 0.25 * atr)
            held = (d * (post["c"] - neck) >= -0.25 * atr).all()
            pressure = d * (last["c"] - last["o"]) > 0
            conf = {
                "htf_aligned": ctx.regime == ("TREND_UP" if d == 1 else "TREND_DOWN"),
                "second_touch": True,
                "neckline_break": True,
                "neckline_retest": bool(near.iloc[-2:].any() and held),
                "buying_pressure": bool(pressure and d * (last["c"] - neck) > 0),
                "killzone": ctx.killzone is not None,
                "fresh_trend": ctx.m15.fresh,
            }
            retest_extreme = float(post["l"].min()) if d == 1 else float(post["h"].max())
            stop = retest_extreme - d * buffer(ctx, cfg)
            name = "double bottom" if d == 1 else "double top"
            meta = {"pattern": name, "neckline": round(neck, 6)}
            notes = [f"{name}, neckline {neck:.5f} cassée", "retour sur la neckline" if conf["neckline_retest"] else "pas de retour"]
            return build_setup(ctx, NAME, direction, float(last["c"]), float(stop), conf, ESSENTIAL, notes, cfg, meta)
    return None
