"""META-SKILL 1 — Revue adversariale d'un setup (anti biais de confirmation).

Pour chaque candidat qualifié, le « critique » cherche :
  - la meilleure raison pour laquelle le trade pourrait être faux ;
  - les éléments du contexte qui contredisent l'entrée ;
  - les risques cachés ;
  - la condition observable qui invaliderait immédiatement la thèse.

Ce module NE DÉCIDE RIEN : il ne bloque aucun trade et ne modifie aucune règle. Sa sortie est journalisée
(et transmise au LLM s'il est activé). La décision reste celle des règles validées et du Risk Manager.
Toute observation récurrente passe par : observation → hypothèse → backtest → validation → OOS → intégration.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from .. import fx

EVIDENCE = Path(__file__).resolve().parents[2] / "knowledge" / "strategy_evidence.yaml"

# poids = gravité relative de chaque objection (sert à choisir la « meilleure raison », pas à décider)
W = {"evidence": 5, "htf": 4, "target_reach": 4, "blocked": 3, "news": 3, "zone": 2, "volatility": 2,
     "spread": 2, "session_end": 2, "journal": 2, "stale": 1, "optional": 1}


@lru_cache(maxsize=1)
def evidence() -> dict:
    try:
        return yaml.safe_load(EVIDENCE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def review(setup, ctx, cfg: dict, journal_stats: dict | None = None) -> dict:
    """Renvoie {best_reason_wrong, contradictions[], hidden_risks[], invalidation, severity, objections[]}.
    `journal_stats` (optionnel) : {strategy: {"n":…, "exp_r":…}} calculé sur le journal paper."""
    d = 1 if setup.direction == "BUY" else -1
    pip = fx.pip_size(setup.symbol)
    risk = abs(setup.entry - setup.stop)
    reward = abs(setup.target - setup.entry)
    atr = ctx.atr_m5 or 0.0
    obj = []                                    # (poids, type, texte, catégorie)

    def add(kind, text, cat):
        obj.append((W[kind], kind, text, cat))

    # preuves historiques de la stratégie (recherche V4)
    ev = (evidence().get("strategies") or {}).get(setup.strategy)
    if ev and ev.get("verdict") in ("DROP", "INSUFFICIENT_DATA"):
        add("evidence", f"{setup.strategy} : verdict {ev['verdict']} en recherche V4 ({ev.get('n')} trades, "
                        f"{ev.get('exp_r')} R/trade) — {ev.get('note', '')}", "hidden")
    # cible atteignable en 30 min ?
    typ = float((evidence().get("general") or {}).get("typical_30min_range_atr_m5", 2.3))
    if atr > 0 and reward > typ * atr:
        add("target_reach", f"cible à {reward / atr:.1f} ATR M5 alors que l'amplitude typique en 30 min est ≈ {typ} ATR : "
                            "elle sera probablement hors de portée avant la sortie au temps", "hidden")
    # tendance de fond opposée
    for tf, v in (("H1", ctx.h1), ("M15", ctx.m15)):
        opp = "down" if d == 1 else "up"
        if getattr(v, "trend", None) == opp or getattr(v, "struct_trend", None) == opp:
            add("htf", f"tendance {tf} opposée au trade ({v.trend} / structure {v.struct_trend})", "context")
            break
    # niveau opposé avant la cible
    lv = ctx.levels_beyond(setup.entry, d)
    if lv and risk > 0:
        p, name = lv[0]
        dist = abs(p - setup.entry)
        if dist < reward and dist < risk:
            add("blocked", f"{name} à {dist / pip:.1f} pips, avant même 1 R : le prix doit le traverser", "context")
    # premium / discount (ICT)
    zone = ctx.zone(ctx.mid)
    if (d == 1 and zone == "premium") or (d == -1 and zone == "discount"):
        add("zone", f"{'achat' if d == 1 else 'vente'} en zone {zone} du range 24 h", "context")
    # annonces
    if ctx.news_block:
        add("news", f"annonce proche : {ctx.news_block}", "context")
    # volatilité
    if ctx.volatility in ("high", "extreme", "low", "dead") or (ctx.vol_ratio and ctx.vol_ratio > 1.5):
        add("volatility", f"volatilité {ctx.volatility} (ratio {ctx.vol_ratio:.2f}) : comportement moins prévisible", "hidden")
    # coût
    spread = ctx.ask - ctx.bid
    if risk > 0 and spread / risk > 0.10:
        add("spread", f"spread = {spread / risk:.0%} du risque : coût élevé pour un trade de 30 min", "hidden")
    # fin de fenêtre de session
    end = max((b for a, b in cfg.get("sessions", {}).get("new_trades_utc", []) if a <= ctx.time.hour < b), default=None)
    if end is not None and (end * 60 - (ctx.time.hour * 60 + ctx.time.minute)) <= 30:
        add("session_end", "dernières 30 min de la fenêtre de trading : liquidité qui baisse", "context")
    # journal paper de la stratégie
    js = (journal_stats or {}).get(setup.strategy)
    if js and js.get("n", 0) >= 10 and (js.get("exp_r") or 0) < 0:
        add("journal", f"journal paper : {js['n']} trades, {js['exp_r']:+.2f} R/trade sur cette stratégie", "hidden")
    # confirmations optionnelles absentes
    missing = [k for k, v in setup.confirmations.items() if not v and k not in setup.essential]
    if missing:
        add("optional", "confirmations optionnelles absentes : " + ", ".join(missing), "context")

    obj.sort(key=lambda x: -x[0])
    best = obj[0][2] if obj else "aucune objection forte trouvée dans les données disponibles"
    prot = (ctx.m15.protected if getattr(ctx.m15, "protected", None) is not None else None)
    dec = 3 if pip == 0.01 else 5
    side = "sous" if d == 1 else "au-dessus de"
    inval = [f"clôture M5 {side} {setup.stop:.{dec}f} (stop)"]
    if prot is not None and d * (setup.entry - prot) > 0:
        inval.append(f"clôture M15 {side} {prot:.{dec}f} (niveau protégé M15)")
    inval.append(f"régime {ctx.regime} qui bascule")
    return {
        "best_reason_wrong": best,
        "contradictions": [t for _, _, t, c in obj if c == "context"],
        "hidden_risks": [t for _, _, t, c in obj if c == "hidden"],
        "invalidation": " ; ou ".join(inval),
        "severity": int(sum(w for w, *_ in obj)),
        "objections": [k for _, k, _, _ in obj],
        "note": "revue informative : ne bloque rien, la décision reste aux règles validées et au Risk Manager",
    }
