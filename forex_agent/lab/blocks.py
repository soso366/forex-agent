"""Définition des blocs A → D et verrouillage séquentiel.

Chaque paramètre est testé SEUL autour de sa valeur actuelle (grille fixée ici, avant les résultats),
sur la configuration verrouillée des blocs précédents. Un réglage n'est retenu que s'il passe TOUS
les critères de stats.ROBUSTNESS. Les réglages retenus d'un bloc sont ensuite combinés et revérifiés
ensemble ; en cas de conflit, ils sont ajoutés un par un (par ordre de gain) et gardés seulement
s'ils passent encore les critères. Le risque monétaire n'est jamais modifié.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from ..brain import router
from .runner import Variant

ALL = ("TrendPullback_v2", "BreakRetest_v2", "FlagBreakout_v1", "DoubleTopBottom_v1", "SweepMSS_v2", "RangeFade_v2")


@dataclass
class Param:
    block: str
    name: str            # nom lisible
    section: str         # section de config (ou "lab" pour un filtre du lab)
    key: str
    grid: list
    base: object
    rescan: tuple = ()
    reclassify: bool = False
    note: str = ""
    none_like: str = "max"   # « désactivé » équivaut à la valeur extrême de ce côté de la grille

    def variant(self, value, locked: dict) -> Variant:
        ov = copy.deepcopy(locked.get("overrides", {}))
        lab = copy.deepcopy(locked.get("lab", {}))
        if self.section == "lab":
            lab[self.key] = value
        elif self.section == "trading.hours":
            ov.setdefault("sessions", {})["new_trades_utc"] = [list(value)]
        else:
            ov.setdefault(self.section, {})[self.key] = value
        rescan = tuple(sorted(set(self.rescan) | set(locked.get("rescan", ()))))
        return Variant(self.block, self.name, value, ov, rescan, self.reclassify or locked.get("reclassify", False),
                       locked.get("matrix"), lab)


def block_a() -> list[Param]:
    m = "management"
    return [
        Param("A", "min R:R (net de spread)", "risk", "min_rr", [1.2, 1.3, 1.5, 1.75, 2.0, 2.5], 1.5),
        Param("A", "cible : marge avant le niveau (ATR)", "strategy_params", "target_offset_atr",
              [0.0, 0.05, 0.1, 0.2, 0.3], 0.05),
        Param("A", "break-even à (R)", m, "breakeven_at_r", [None, 0.5, 0.75, 1.0, 1.25, 1.5], 1.0),
        Param("A", "protection du profit : déclenchement (R)", m, "lock_at_r", [None, 1.25, 1.5, 2.0, 2.5], 1.5),
        Param("A", "protection du profit : R verrouillé", m, "lock_r", [0.25, 0.5, 0.75, 1.0], 0.5),
        Param("A", "trailing EMA20 : dès (R)", m, "trail_ema20_after_r", [None, 0.5, 0.75, 1.0, 1.5, 2.0], 1.0),
        Param("A", "trailing : décalage (ATR)", m, "trail_offset_atr", [0.1, 0.2, 0.3, 0.5, 0.75], 0.3),
        Param("A", "prise de profit près de la cible", m, "take_profit_near_target", [None, 0.6, 0.7, 0.8, 0.9], 0.8),
        Param("A", "sortie sur displacement contraire (ATR)", m, "opposite_displacement_atr",
              [None, 0.8, 1.0, 1.2, 1.5, 2.0], 1.2),
        Param("A", "sortie momentum contre sous (R)", m, "momentum_exit_r", [None, -0.1, -0.2, -0.3, -0.5, -0.7], -0.3,
              none_like="min"),
        Param("A", "sortie si le régime se retourne", m, "regime_flip_exit", [True, False], True),
        Param("A", "sortie si CHOP et en perte", m, "chop_exit", [True, False], True),
        Param("A", "durée max (min, ≤ 30 imposé)", "trading", "max_hold_minutes", [15, 20, 25, 30], 30),
    ]


def block_b() -> list[Param]:
    return [
        Param("B", "killzone obligatoire", "lab", "require_killzone", [False, True], False),
        Param("B", "paire exclue", "lab", "exclude_symbols", [[], ["EURUSD"], ["GBPUSD"], ["USDJPY"]], []),
        Param("B", "volatilité exclue", "lab", "exclude_volatility", [[], ["high"], ["low"], ["high", "low"]], []),
        Param("B", "spread max / stop", "risk", "max_spread_to_stop_ratio", [0.15, 0.2, 0.25, 0.3, 0.4], 0.25),
        Param("B", "seuil de spike (ATR / médiane)", "regime", "vol_extreme_ratio", [2.0, 2.25, 2.5, 3.0, 3.5], 2.5,
              reclassify=True),
        Param("B", "marché mort (ATR < x spread)", "regime", "dead_atr_spread_mult", [0.8, 1.0, 1.2, 1.5, 2.0], 1.2,
              reclassify=True),
    ]


SESSION_STARTS = [6, 7, 8, 9]
SESSION_ENDS = [15, 16, 17, 18, 19, 20]


def block_b_sessions() -> Param:
    return Param("B", "horaires d'entrée (UTC)", "trading.hours", "new_trades_utc",
                 [(a, b) for a in SESSION_STARTS for b in SESSION_ENDS], (7, 20))


def block_c() -> list[Param]:
    s = "strategy_params"
    return [
        Param("C", "stop : tampon au-delà de l'invalidation (ATR)", s, "stop_buffer_atr",
              [0.3, 0.4, 0.5, 0.6, 0.75, 1.0], 0.5, rescan=ALL),
        Param("C", "TrendPullback : pullback minimal", s, "min_pullback_pct", [0.2, 0.25, 0.3, 0.382, 0.5], 0.3,
              rescan=("TrendPullback_v2",)),
        Param("C", "TrendPullback : zone de valeur (ATR)", s, "tp_value_zone_atr", [0.2, 0.3, 0.4, 0.5], 0.3,
              rescan=("TrendPullback_v2",)),
        Param("C", "tendance fraîche : cassures max", "regime", "fresh_max_bos", [2, 3, 4, 6], 3, rescan=ALL[:4]),
        Param("C", "impulsion contraire à l'entrée (ATR)", s, "opposite_displacement_atr", [1.0, 1.25, 1.5, 2.0, 3.0],
              1.5, rescan=("TrendPullback_v2", "BreakRetest_v2")),
        Param("C", "BreakRetest : zone de retest (ATR)", s, "br_zone_atr", [0.15, 0.2, 0.25, 0.3, 0.4], 0.25,
              rescan=("BreakRetest_v2",)),
        Param("C", "BreakRetest : cassure minimale (ATR)", s, "br_break_min_atr", [0.05, 0.1, 0.15, 0.2], 0.1,
              rescan=("BreakRetest_v2",)),
        Param("C", "Flag : mât minimal (ATR)", s, "flag_pole_atr", [1.5, 2.0, 2.5, 3.0, 3.5], 2.5,
              rescan=("FlagBreakout_v1",)),
        Param("C", "Flag : corps de cassure (ATR)", s, "flag_break_body_atr", [0.3, 0.4, 0.5, 0.6, 0.75], 0.5,
              rescan=("FlagBreakout_v1",)),
        Param("C", "DoubleTop/Bottom : retour neckline (ATR)", s, "dt_retest_atr", [0.15, 0.2, 0.25, 0.3, 0.4], 0.25,
              rescan=("DoubleTopBottom_v1",)),
        Param("C", "equal highs/lows : tolérance (ATR)", "regime", "equal_level_tol_atr", [0.05, 0.1, 0.15, 0.2], 0.1,
              rescan=ALL),
        Param("C", "SweepMSS : displacement minimal (ATR)", s, "displacement_atr", [0.6, 0.8, 1.0, 1.2], 1.0,
              rescan=("SweepMSS_v2",)),
    ]


def block_d() -> list[Param]:
    return [
        Param("D", "stratégie désactivée", "lab", "disable_strategies", [[]] + [[n] for n in ALL if n != "SweepMSS_v2"],
              []),
        Param("D", "tendance : efficiency minimale", "regime", "er_trend_min", [0.2, 0.25, 0.3, 0.35, 0.4], 0.3,
              reclassify=True),
        Param("D", "range : efficiency maximale", "regime", "er_range_max", [0.15, 0.2, 0.25, 0.3], 0.25,
              reclassify=True),
    ]


def numeric_neighbors(p: Param, value) -> list:
    """Voisins dans la grille (hors valeur de référence). None/booléens/listes : pas de voisinage."""
    nums = sorted(v for v in p.grid if isinstance(v, (int, float)) and not isinstance(v, bool))
    if value is None and nums:                       # « désactivé » : voisin = valeur la moins active
        ext = nums[-1] if p.none_like == "max" else nums[0]
        return [ext] if ext != p.base else []
    if value not in nums:
        return []
    i = nums.index(value)
    return [nums[j] for j in (i - 1, i + 1) if 0 <= j < len(nums) and nums[j] != p.base]
