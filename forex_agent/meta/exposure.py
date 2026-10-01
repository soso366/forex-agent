"""META-SKILL 2 — Audit d'exposition / corrélation avant une position simultanée.

Exemple : EURUSD long + GBPUSD long = deux fois « vendeur d'USD ».
Mesure : devises communes, sens de l'exposition, corrélation récente des P&L, risque macro commun, exposition totale.
Ce module est INFORMATIF : le Risk Manager garde le dernier mot (sa règle « même devise, même sens » reste la seule
qui bloque). Rien ici ne modifie la taille ni n'autorise un trade refusé.
"""
from __future__ import annotations

import math
from datetime import timedelta

import numpy as np
import pandas as pd

from .. import fx


def legs(symbol: str, direction: str, risk_eur: float) -> dict[str, float]:
    """Exposition signée par devise, en € de risque : acheter EURUSD = +EUR / −USD."""
    base, quote = fx.split(symbol)
    s = 1 if direction == "BUY" else -1
    return {base: s * risk_eur, quote: -s * risk_eur}


def recent_corr(provider, a: str, b: str, now, days: int = 5) -> float | None:
    """Corrélation des rendements M5 (mid) sur les derniers jours."""
    try:
        n = int(days * 288)
        ca = provider.candles(a, "M5", now, n)["c"]
        cb = provider.candles(b, "M5", now, n)["c"]
        df = pd.concat([ca.rename("a"), cb.rename("b")], axis=1).dropna()
        r = np.log(df).diff().dropna()
        if len(r) < 100:
            return None
        return float(r["a"].corr(r["b"]))
    except Exception:
        return None


def upcoming_macro(cfg: dict, now, currencies: set[str], hours: int = 2) -> list[str]:
    from ..analysis.structure import first_friday, NY
    from datetime import datetime
    out = []
    n = cfg.get("news", {})
    events = []
    if n.get("auto_nfp", True):
        ff = first_friday(now.year, now.month)
        events.append(("NFP", datetime(ff.year, ff.month, ff.day, 8, 30, tzinfo=NY).astimezone(now.tzinfo), ["USD"]))
    for e in n.get("events", []) or []:
        t = pd.Timestamp(e["time"])
        t = (t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")).to_pydatetime()
        events.append((e.get("name", "annonce"), t, e.get("currencies", [])))
    for name, t, ccys in events:
        if now <= t <= now + timedelta(hours=hours) and (not ccys or set(ccys) & currencies):
            out.append(f"{name} à {t:%H:%M} UTC ({', '.join(ccys) or 'toutes devises'})")
    return out


def audit(candidate: dict, open_trades: list[dict], provider, now, cfg: dict) -> dict:
    """candidate : {symbol, direction, risk_eur}. open_trades : lignes du journal (symbol, direction, risk_eur)."""
    if not open_trades:
        return {"applies": False}
    pos = [{"symbol": t["symbol"], "direction": t["direction"], "risk_eur": float(t.get("risk_eur") or 0)}
           for t in open_trades] + [candidate]
    net: dict[str, float] = {}
    for p in pos:
        for c, v in legs(p["symbol"], p["direction"], p["risk_eur"]).items():
            net[c] = net.get(c, 0.0) + v
    new = legs(candidate["symbol"], candidate["direction"], 1)
    pairs, notes = [], []
    eff_var = sum(p["risk_eur"] ** 2 for p in pos)
    for t in pos[:-1]:
        old = legs(t["symbol"], t["direction"], 1)
        common = sorted(set(old) & set(new))
        same = [c for c in common if np.sign(old[c]) == np.sign(new[c])]
        opp = [c for c in common if np.sign(old[c]) != np.sign(new[c])]
        rho = recent_corr(provider, t["symbol"], candidate["symbol"], now)
        # corrélation des P&L : celle des prix × sens des deux positions
        sgn = (1 if t["direction"] == "BUY" else -1) * (1 if candidate["direction"] == "BUY" else -1)
        pnl_rho = None if rho is None else rho * sgn
        if pnl_rho is not None:
            eff_var += 2 * pnl_rho * t["risk_eur"] * candidate["risk_eur"]
        pairs.append({"with": t["symbol"], "common_currency": common, "same_direction": same, "opposite": opp,
                      "price_corr_5d": None if rho is None else round(rho, 2),
                      "pnl_corr_5d": None if pnl_rho is None else round(pnl_rho, 2)})
        if same:
            notes.append(f"{candidate['symbol']} {candidate['direction']} + {t['symbol']} {t['direction']} : "
                         f"même exposition {', '.join(same)} (risque doublé sur cette devise)")
        elif pnl_rho is not None and pnl_rho > 0.5:
            notes.append(f"P&L fortement corrélés avec {t['symbol']} (ρ ≈ {pnl_rho:.2f}) malgré des devises différentes")
        elif opp:
            notes.append(f"exposition {', '.join(opp)} opposée à {t['symbol']} : couverture partielle")
    gross = sum(p["risk_eur"] for p in pos)
    eff = math.sqrt(max(eff_var, 0))
    ccys = set(net)
    macro = upcoming_macro(cfg, now, ccys)
    return {
        "applies": True,
        "net_exposure_eur": {c: round(v, 3) for c, v in sorted(net.items(), key=lambda x: -abs(x[1]))},
        "pairs": pairs,
        "gross_risk_eur": round(gross, 3),
        "effective_risk_eur": round(eff, 3),          # risque « réel » tenant compte des corrélations
        "diversification": round(eff / gross, 2) if gross else None,  # 1 = aucune diversification
        "macro_common_risk": macro,
        "notes": notes,
        "note": "audit informatif : le Risk Manager garde le dernier mot",
    }
