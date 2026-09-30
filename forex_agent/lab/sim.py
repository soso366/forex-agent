"""Simulateur du Parameter Lab : rejoue le VRAI cycle (cycle.run_cycle, PaperBroker, RiskManager,
positions.evaluate) en lisant le cache au lieu de recalculer l'analyse.

Seules deux fonctions du cycle sont remplacées pendant la simulation :
- _load_contexts : contextes lus dans le cache (régime/killzone/annonces recalculés si la config change) ;
- scan_symbol    : setups lus dans le cache puis REQUALIFIÉS avec la config testée
                   (min R:R, spread, annonces, filtres du Bloc B), ou recalculés pour les stratégies
                   dont on teste un paramètre (Bloc C).
Le journal des cycles n'est pas écrit (inutile pour les mesures) ; les trades le sont, en mémoire.
Le test de référence vérifie que la configuration V2 reproduit exactement le backtest GitHub.
"""
from __future__ import annotations

import copy
import pickle
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd

from .. import cycle as cycle_mod
from ..analysis.market import classify, rp
from ..analysis.structure import killzone, liquidity_pools, news_blackout
from ..brain import router
from ..brain.router import STRATEGIES, ScanResult, allowed
from ..data.providers import CSVProvider
from ..fx import conversion_symbols
from ..journal import Store
from ..strategies.base import qualifies
from .cache import cycle_times


class _LazyFull:
    """Contextes complets chargés jour par jour (le cycle avance chronologiquement)."""

    def __init__(self, directory: Path):
        self.dir, self.day, self.data = directory, None, {}

    def get(self, key):
        now, _ = key
        day = now.strftime("%Y-%m-%d")
        if day != self.day:
            p = self.dir / f"full_{day}.pkl"
            self.data = pickle.load(open(p, "rb")) if p.exists() else {}
            self.day = day
        return self.data.get(key)

    def __bool__(self):
        return True


class LabData:
    """Cache : petits contextes en mémoire, contextes complets lus jour par jour."""

    def __init__(self, cache_dir: str | Path, csv_dir: str | Path, cfg: dict, need_full: bool = False):
        self.dir = Path(cache_dir)
        self.small, self.scans = {}, {}
        self.full = _LazyFull(self.dir)
        for p in sorted(self.dir.glob("small_*.pkl")):
            with open(p, "rb") as f:
                d = pickle.load(f)
            self.small.update(d["small"])
            self.scans.update(d["scans"])
        symbols = list(cfg["symbols"]) + [s for s in conversion_symbols(cfg["symbols"], cfg["account"]["currency"])
                                          if s not in cfg["symbols"]]
        self.provider = CSVProvider(symbols, csv_dir)

    def load_full(self):
        pass


def _reclassify(ctx, cfg):
    """Régime / volatilité recalculés si la définition des régimes change (Bloc D)."""
    touch_hi, touch_lo = ctx.range_touches
    vol, strength, regime, why = classify(ctx.h1, ctx.m15, ctx.er_m15, ctx.vol_ratio, ctx.atr_m5_pips,
                                          ctx.spread_pips, ctx.range_width_atr, touch_hi, touch_lo, cfg)
    if regime == ctx.regime and vol == ctx.volatility:
        return ctx
    c = copy.copy(ctx)
    c.volatility, c.trend_strength, c.regime, c.regime_reason = vol, strength, regime, why
    return c


def _set_fresh(ctx, cfg):
    for v in (ctx.h1, ctx.m15):
        if v.fresh_max_bos != rp(cfg, "fresh_max_bos") or v.fresh_max_ext_atr != rp(cfg, "fresh_max_ext_atr"):
            v.fresh_max_bos, v.fresh_max_ext_atr = rp(cfg, "fresh_max_bos"), rp(cfg, "fresh_max_ext_atr")


def requalify(setup, ctx, cfg):
    """Conditions dépendant de la config testée, recalculées exactement comme build_setup."""
    from ..strategies.base import sp
    s = copy.copy(setup)
    s.confirmations = dict(setup.confirmations)
    d = 1 if s.direction == "BUY" else -1
    spread = ctx.ask - ctx.bid
    off = sp(cfg, "target_offset_atr")
    if off != 0.05 and not str(s.meta.get("target_level", "")).startswith("espace libre"):
        dec = 3 if s.symbol.endswith("JPY") else 5
        s.target = round(s.target - d * (off - 0.05) * ctx.atr_m5, dec)   # exactement build_setup
    risk = d * (s.entry - s.stop)
    reward = d * (s.target - s.entry)
    net_rr = (reward - spread) / (risk + spread) if reward > 0 else 0.0
    if "rr" in s.confirmations:
        s.confirmations["rr"] = net_rr >= cfg["risk"].get("min_rr", 1.5)
    if "spread" in s.confirmations:
        s.confirmations["spread"] = spread <= cfg["risk"].get("max_spread_to_stop_ratio", 0.25) * risk
    if "news" in s.confirmations:
        s.confirmations["news"] = not ctx.news_block
    return s


def block_b_filter(setup, ctx, lab: dict) -> str | None:
    """Filtres testés au Bloc B (n'existent pas en production tant qu'ils ne sont pas validés)."""
    if setup.symbol in lab.get("exclude_symbols", []):
        return f"filtre lab : paire {setup.symbol} exclue"
    if lab.get("require_killzone") and not ctx.killzone:
        return "filtre lab : hors killzone"
    if ctx.volatility in lab.get("exclude_volatility", []):
        return f"filtre lab : volatilité {ctx.volatility}"
    if ctx.session in lab.get("exclude_sessions", []):
        return f"filtre lab : session {ctx.session}"
    if setup.strategy in lab.get("disable_strategies", []):
        return f"filtre lab : {setup.strategy} désactivée"
    return None


class Engine:
    def __init__(self, data: LabData):
        self.data = data

    # ------------------------------------------------------------------ remplacements du cycle
    def _contexts(self, cfg, now):
        contexts, errors = {}, {}
        zones = cfg.get("sessions", {}).get("killzones_ny", {"london": [2, 5], "new_york_am": [7, 10]})
        for sym in cfg["symbols"]:
            src = (self.data.full.get((now, sym)) if self.use_full else None) or self.data.small.get((now, sym))
            if src is None:
                errors[sym] = "absent du cache"
                continue
            if isinstance(src, str):
                errors[sym] = src
                continue
            ctx = _reclassify(src, cfg) if self.reclassify else src
            kz = killzone(now, zones)
            blocked, why = news_blackout(now, sym, cfg)
            nb = why if blocked else ""
            if kz != ctx.killzone or nb != ctx.news_block:
                ctx = copy.copy(ctx)
                ctx.killzone, ctx.news_block = kz, nb
            tol = rp(cfg, "equal_level_tol_atr")
            if tol != 0.1 and "H1" in ctx.frames:          # définition des equal highs/lows testée (Bloc C)
                ctx = copy.copy(ctx)
                asia = tuple(cfg.get("sessions", {}).get("asia_utc", (0, 7)))
                ctx.pools = liquidity_pools(ctx.frames["H1"], ctx.frames["M15"], now, ctx.m15.atr, asia, tol)
            _set_fresh(ctx, cfg)
            contexts[sym] = ctx
        return contexts, errors

    def _scan(self, ctx, cfg):
        now, sym = ctx.time, ctx.symbol
        res = ScanResult(sym)
        plan = self.matrix.get(ctx.regime, [])
        if not plan:
            res.rejections.append(f"régime {ctx.regime} : aucune stratégie adaptée ({ctx.regime_reason})")
            return res
        base = self.data.scans.get((now, sym))
        cached = {(s.strategy, s.direction): s for s in (base.setups if base is not None else [])}
        small = self.data.small.get((now, sym))
        base_regime = small.regime if small is not None and not isinstance(small, str) else None
        base_plan = set(router.REGIME_MATRIX.get(base_regime, [])) if base_regime else set()
        for name, direction in plan:
            ok, why = allowed(name, cfg)
            label = f"{name}:{direction}"
            if not ok:
                res.rejections.append(f"{label} {why}")
                continue
            res.considered.append(label)
            live = (name in self.rescan or (name, direction) not in base_plan
                    or ctx.regime != base_regime)
            if live:
                if len(ctx.frames.get("M5", ())) <= 2:   # hors fenêtre d'entrée : aucune position possible
                    res.rejections.append(f"{label} : hors fenêtre (non recalculé)")
                    continue
                try:
                    setup = STRATEGIES[name].scan(ctx, direction, cfg)
                except Exception as e:
                    res.rejections.append(f"{label} erreur : {e}")
                    continue
            else:
                setup = cached.get((name, direction))
                if setup is not None:
                    setup = requalify(setup, ctx, cfg)
            if setup is None:
                res.rejections.append(f"{label} : motif absent")
                continue
            if not setup.id:
                setup.id = f"{sym}{label}{now}"
            res.setups.append(setup)
            good, why = qualifies(setup, cfg["trading"])
            if good:
                blocked = block_b_filter(setup, ctx, self.lab)
                if blocked:
                    res.rejections.append(f"{label} : {blocked}")
                else:
                    res.qualified.append(setup)
            else:
                res.rejections.append(f"{label} : {why}")
        return res

    # ------------------------------------------------------------------ simulation
    def run(self, cfg: dict, start: datetime, end: datetime, rescan: set[str] | None = None,
            reclassify: bool = False, matrix: dict | None = None, lab: dict | None = None) -> pd.DataFrame:
        self.rescan = set(rescan or [])
        self.reclassify = reclassify
        self.matrix = matrix or router.REGIME_MATRIX
        self.use_full = bool(self.rescan or reclassify or matrix is not None)
        self.lab = lab or {}
        if self.use_full:
            self.data.load_full()
        store = Store(":memory:")
        with _patched(self):
            for now in cycle_times(cfg, start, end):
                cycle_mod.run_cycle(cfg, self.data.provider, store, now)
        trades = pd.DataFrame([dict(r) for r in store.db.execute("SELECT * FROM trades ORDER BY id")])
        store.close()
        return trades


@contextmanager
def _patched(engine: Engine):
    saved = (cycle_mod._load_contexts, cycle_mod.scan_symbol, cycle_mod.load_prompt, Store.log_cycle)
    cycle_mod._load_contexts = lambda cfg, provider, now: engine._contexts(cfg, now)
    cycle_mod.scan_symbol = engine._scan
    cycle_mod.load_prompt = lambda cfg: ("", "lab")
    Store.log_cycle = lambda self, record, snapshots, ideas: 0
    try:
        yield
    finally:
        cycle_mod._load_contexts, cycle_mod.scan_symbol, cycle_mod.load_prompt, Store.log_cycle = saved
