"""SweepMSS_v2 — modèle ICT minimal (synthèse des 41 épisodes).

Séquence obligatoire : biais HTF → fenêtre horaire (killzone) → prise d'une liquidité NOMMÉE
(PDL, bas Asie, equal lows, bas du jour, swing…) → displacement → Market Structure Shift →
FVG créée par le displacement → RETRACEMENT dans la FVG (jamais d'entrée en chasse) →
cible = liquidité opposée → stop derrière l'extrême du sweep.
Observation ≠ interprétation : le code ne mesure que des faits observables (prix, heures,
gaps, clôtures) ; « prise de liquidité » est l'interprétation ICT de ces faits.
"""
from __future__ import annotations

from ..analysis import indicators as ind
from ..analysis import structure as st
from ..analysis.market import MarketContext
from .base import build_setup, buffer, params, sign_of

NAME = "SweepMSS_v2"
ESSENTIAL = ["bias", "time", "sweep", "displacement", "mss", "fvg", "retracement", "premium_discount"]


def scan(ctx: MarketContext, direction: str, cfg: dict):
    d = sign_of(direction)
    m5 = ctx.frames["M5"]
    n = len(m5)
    atr = ctx.atr_m5
    side = "SSL" if d == 1 else "BSL"              # un achat suit une prise de sell-side liquidity
    pools = [p for p in ctx.pools if p["side"] == side]
    if not pools:
        return None

    # 1. prise de liquidité dans les 8 dernières M5 (mèche au-delà, clôture revenue du bon côté)
    sweep_pos, swept = None, None
    for j in range(n - 8, n - 1):
        bar = m5.iloc[j]
        wick = bar["l"] if d == 1 else bar["h"]
        for pl in pools:
            beyond = d * (pl["price"] - wick) >= 0.05 * atr
            back = d * (bar["c"] - pl["price"]) > 0 or d * (m5["c"].iloc[j + 1] - pl["price"]) > 0
            before_ok = (d * (m5["l" if d == 1 else "h"].iloc[j - 12:j] - pl["price"]) > 0).all()
            if beyond and back and before_ok:
                sweep_pos, swept = j, pl
                break
        if sweep_pos is not None:
            break
    if sweep_pos is None:
        return None

    # 2. displacement + MSS : clôture au-delà du dernier swing mineur antérieur au sweep
    pre = m5.iloc[max(0, sweep_pos - 20):sweep_pos + 1]
    highs, lows = ind.swings(pre, 2, 2)
    minor = (highs[-1][1] if highs else float(pre["h"].iloc[-6:].max())) if d == 1 else \
            (lows[-1][1] if lows else float(pre["l"].iloc[-6:].min()))
    after = m5.iloc[sweep_pos + 1:]
    disp_mult = params(cfg).get("displacement_atr", 1.0)
    displacement = any(st.displacement_bar(after.iloc[k], atr, d, disp_mult) for k in range(len(after)))
    mss = bool((d * (after["c"] - minor) > 0).any())

    # 3. FVG créée après le sweep, non invalidée ; entrée seulement au retracement dedans
    gaps = st.fvgs(m5, sweep_pos, d)
    fvg = gaps[-1] if gaps else None
    last = m5.iloc[-1]
    retracement = False
    if fvg:
        k, lo, hi = fvg
        since = m5.iloc[k + 1:]
        intact = not ((since["c"] < lo).any() if d == 1 else (since["c"] > hi).any())
        touched = (last["l"] <= hi and last["c"] >= lo) if d == 1 else (last["h"] >= lo and last["c"] <= hi)
        in_zone = lo - 0.1 * atr <= ctx.mid <= hi + 0.1 * atr
        retracement = intact and k < n - 1 and (touched or in_zone)

    against = "down" if d == 1 else "up"
    entry = float(last["c"])
    conf = {
        "bias": ctx.regime in ("RANGE", "TREND_UP" if d == 1 else "TREND_DOWN") and ctx.h1.struct_trend != against,
        "time": ctx.killzone is not None,
        "sweep": True,
        "displacement": displacement,
        "mss": mss,
        "fvg": fvg is not None,
        "retracement": retracement,
        "premium_discount": ctx.zone(entry) == ("discount" if d == 1 else "premium"),
        # optionnelles
        "external_liquidity": swept["kind"] == "external",
        "htf_aligned": ctx.h1.struct_trend == ("up" if d == 1 else "down"),
    }
    stop = (float(m5["l"].iloc[sweep_pos:].min()) if d == 1 else float(m5["h"].iloc[sweep_pos:].max())) \
        - d * buffer(ctx, cfg)
    meta = {"liquidity_taken": swept["name"], "liquidity_price": round(swept["price"], 6),
            "sweep_time": str(m5.index[sweep_pos]), "fvg": [round(x, 6) for x in fvg[1:]] if fvg else None,
            "killzone": ctx.killzone, "price_zone": ctx.zone(entry)}
    notes = [f"{side} « {swept['name']} » prise à {m5.index[sweep_pos]:%H:%M}",
             "MSS" if mss else "pas de MSS", "retracement dans la FVG" if retracement else "pas de retracement FVG"]
    return build_setup(ctx, NAME, direction, entry, float(stop), conf, ESSENTIAL, notes, cfg, meta)
