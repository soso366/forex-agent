"""Strategy Router : MARCHÉ -> CONTEXTE -> STRATÉGIE.

Le régime détermine quelles stratégies ont le droit d'être évaluées. En CHOP,
DEAD ou VOLATILE, aucune stratégie n'est appelée : NO TRADE."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..analysis.market import MarketContext
from ..config import Setup
from ..strategies import (break_retest, double_top_bottom, flag_breakout, range_fade, sweep_mss,
                          trend_pullback)
from ..strategies.base import qualifies

STRATEGIES = {m.NAME: m for m in (trend_pullback, break_retest, flag_breakout, double_top_bottom,
                                  sweep_mss, range_fade)}

_TREND = ["TrendPullback_v2", "BreakRetest_v2", "FlagBreakout_v1", "DoubleTopBottom_v1", "SweepMSS_v2"]
REGIME_MATRIX: dict[str, list[tuple[str, str]]] = {
    # tendance : uniquement dans le sens de la tendance (continuation)
    "TREND_UP": [(n, "BUY") for n in _TREND],
    "TREND_DOWN": [(n, "SELL") for n in _TREND],
    # range / consolidation : objectifs plus proches, les deux sens (Wysetrade, ICT)
    "RANGE": [("RangeFade_v2", "BUY"), ("RangeFade_v2", "SELL"), ("SweepMSS_v2", "BUY"), ("SweepMSS_v2", "SELL")],
    # marché sans biais clair, mort ou en spike : NO TRADE
    "CHOP": [], "DEAD": [], "VOLATILE": [],
}


@dataclass
class ScanResult:
    symbol: str
    considered: list[str] = field(default_factory=list)
    setups: list[Setup] = field(default_factory=list)       # motifs trouvés (qualifiés ou non)
    qualified: list[Setup] = field(default_factory=list)
    rejections: list[str] = field(default_factory=list)

    @property
    def best(self) -> Setup | None:
        return max(self.qualified, key=lambda s: (s.rr, s.score), default=None)


def allowed(name: str, cfg: dict) -> tuple[bool, str]:
    sc = cfg.get("strategies", {}).get(name, {})
    if not sc.get("enabled", False):
        return False, "désactivée"
    status = sc.get("status", "experimental")
    if status == "experimental" and not cfg["trading"].get("allow_experimental_in_paper", False):
        return False, "expérimentale non autorisée"
    return True, status


def scan_symbol(ctx: MarketContext, cfg: dict) -> ScanResult:
    res = ScanResult(ctx.symbol)
    plan = REGIME_MATRIX.get(ctx.regime, [])
    if not plan:
        res.rejections.append(f"régime {ctx.regime} : aucune stratégie adaptée ({ctx.regime_reason})")
        return res
    for name, direction in plan:
        ok, why = allowed(name, cfg)
        label = f"{name}:{direction}"
        if not ok:
            res.rejections.append(f"{label} {why}")
            continue
        res.considered.append(label)
        try:
            setup = STRATEGIES[name].scan(ctx, direction, cfg)
        except Exception as e:  # une stratégie défaillante ne doit jamais bloquer le cycle
            res.rejections.append(f"{label} erreur : {e}")
            continue
        if setup is None:
            res.rejections.append(f"{label} : motif absent")
            continue
        setup.id = hashlib.sha1(f"{ctx.symbol}{label}{ctx.time}".encode()).hexdigest()[:8]
        res.setups.append(setup)
        good, why = qualifies(setup, cfg["trading"])
        if good:
            res.qualified.append(setup)
        else:
            res.rejections.append(f"{label} : {why}")
    return res
