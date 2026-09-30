"""Gestion active des positions ouvertes (revue à chaque cycle de 5 minutes).

Questions posées à chaque cycle : le setup est-il toujours valide ? le momentum
continue-t-il ? le marché a-t-il changé ? la cible est-elle encore logique ?
faut-il protéger ? faut-il sortir ?"""
from __future__ import annotations

from dataclasses import dataclass

from . import fx
from .analysis.market import MarketContext


@dataclass
class PositionAdvice:
    action: str                 # HOLD | MOVE_STOP | TAKE_PROFIT | CLOSE
    reason: str
    new_stop: float | None = None
    r_multiple: float = 0.0


def evaluate(trade: dict, ctx: MarketContext, mcfg: dict) -> PositionAdvice:
    d = 1 if trade["direction"] == "BUY" else -1
    price = ctx.bid if d == 1 else ctx.ask
    r_unit = d * (trade["entry"] - trade["initial_stop"])
    r_now = d * (price - trade["entry"]) / r_unit if r_unit > 0 else 0.0
    m5 = ctx.frames["M5"].iloc[-1]
    against = "TREND_DOWN" if d == 1 else "TREND_UP"
    strategy = trade.get("strategy", "")

    # 1. le marché a changé contre la position
    if mcfg.get("regime_flip_exit", True) and ctx.regime in (against, "VOLATILE"):
        return PositionAdvice("CLOSE", f"régime devenu {ctx.regime} : contexte invalidé", r_multiple=r_now)
    if (mcfg.get("chop_exit", True) and ctx.regime == "CHOP"
            and not strategy.startswith(("RangeFade", "SweepMSS")) and r_now < 0):
        return PositionAdvice("CLOSE", "tendance disparue (CHOP) et position en perte", r_multiple=r_now)

    # 1bis. invalidation narrative (ICT) : displacement contraire franc
    body = d * (m5["c"] - m5["o"])
    if mcfg.get("opposite_displacement_atr") is not None and body <= -mcfg.get("opposite_displacement_atr", 1.2) * ctx.atr_m5:
        return PositionAdvice("CLOSE", "displacement M5 contraire : scénario invalidé", r_multiple=r_now)

    # 2. momentum clairement contre + position en perte : setup invalidé
    momentum_against = d * (m5["c"] - m5["ema20"]) < 0 and d * (m5["rsi"] - 50) < -mcfg.get("momentum_rsi_band", 5)
    if mcfg.get("momentum_exit_r") is not None and momentum_against and r_now < mcfg.get("momentum_exit_r", -0.3):
        return PositionAdvice("CLOSE", f"momentum M5 contre la position (RSI {m5['rsi']:.0f}), setup invalidé",
                              r_multiple=r_now)

    # 3. proche de la cible et essoufflement : prise de profit
    path = d * (trade["target"] - trade["entry"])
    progress = d * (price - trade["entry"]) / path if path > 0 else 0.0
    if (mcfg.get("take_profit_near_target") is not None and progress >= mcfg["take_profit_near_target"]
            and d * (m5["c"] - m5["ema9"]) < 0):
        return PositionAdvice("TAKE_PROFIT", f"{progress:.0%} du chemin vers la cible et momentum qui se retourne",
                              r_multiple=r_now)

    # 4. protection du trade (resserrer uniquement)
    spread = ctx.ask - ctx.bid
    candidate = None
    if mcfg.get("lock_at_r") is not None and r_now >= mcfg["lock_at_r"]:
        candidate = trade["entry"] + d * mcfg["lock_r"] * r_unit
        why = f"+{r_now:.1f}R : stop verrouille +{mcfg['lock_r']}R"
    elif mcfg.get("breakeven_at_r") is not None and r_now >= mcfg["breakeven_at_r"]:
        candidate = trade["entry"] + d * spread
        why = f"+{r_now:.1f}R : stop au break-even"
    trail_r = mcfg.get("trail_ema20_after_r")
    if trail_r is not None and r_now >= trail_r:                   # trailing EMA20 M5 (vidéo TA)
        trail = m5["ema20"] - d * mcfg.get("trail_offset_atr", 0.3) * ctx.atr_m5
        if candidate is None or d * (trail - candidate) > 0:
            if d * (price - trail) > 0:
                candidate, why = float(trail), f"+{r_now:.1f}R : trailing sous l'EMA20 M5" if d == 1 else \
                    f"+{r_now:.1f}R : trailing au-dessus de l'EMA20 M5"
    pip = fx.pip_size(trade["symbol"])
    if candidate is not None and d * (candidate - trade["stop"]) >= 0.5 * pip:   # pas de micro-ajustements
        dec = 3 if pip == 0.01 else 5
        return PositionAdvice("MOVE_STOP", why, new_stop=round(float(candidate), dec), r_multiple=r_now)

    return PositionAdvice("HOLD", f"setup toujours valide ({ctx.regime}, {r_now:+.2f}R)", r_multiple=r_now)
