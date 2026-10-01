"""Contrôle final de H3 sur le hors-échantillon verrouillé (sept. 2024 → août 2025).

Écrit et commité AVANT de disposer des données. H3 est figée : mode=fade · k=0,5 · days=tous
(stop 1,5 ATR M5, sortie au bout de 30 min, entrée 16:01 Europe/London). Aucun paramètre ne change ici.

Contrôles demandés (dans l'ordre) :
1. Heure du fix = 16:00 Europe/London avec changement d'heure automatique (vérifié sur les trades produits).
2. Résultats : global, par paire, par trimestre, par mois, par jour de semaine.
3. Sensibilité aux coûts : 0,0 / 0,2 / 0,4 / 0,6 / 1,0 pip de spread + glissement TOTAL supplémentaire par trade.
4. Vue par événement (jour de fix) : jours gagnants / perdants, PnL moyen par jour, IC bootstrap par jour,
   et version « une seule paire par jour » (priorité fixe EURUSD > GBPUSD > USDJPY).
5. Concentration : fins de mois, 5 meilleurs jours, meilleur trimestre, meilleure paire.
6. Placebo : EXACTEMENT la même règle à 8 heures prédéfinies (Londres) : 10:00 11:00 12:00 13:00 14:00 15:00 17:00 18:00.

Verdict (règles fixées ici, avant les données) :
- FAIL si espérance ≤ 0 ou profit factor ≤ 1 (coût supplémentaire 0).
- PASS si TOUT est vrai :
    a. espérance > 0 et PF > 1 ;
    b. « sûrement positif » = bootstrap au niveau JOUR DE FIX (somme des R du jour, 10 000 tirages) :
       borne basse de l'IC 95 % de l'espérance quotidienne > 0 (une moyenne positive seule ne suffit pas) ;
    c. au moins 3 trimestres sur 4 positifs (trimestres : sept.–nov., déc.–fév., mars–mai, juin–août) ;
       2/4 = au mieux INCONCLUSIVE ; 0 ou 1/4 = FAIL ;
    d. encore positif sans les fins de mois, sans les 5 meilleurs jours, sans le meilleur trimestre, sans la meilleure paire ;
    e. « une seule paire par jour » positive ;
    f. 16:00 est spécifique : son espérance est STRICTEMENT supérieure à celle des 8 heures placebo ;
    g. exploitable après coûts réalistes : espérance > 0 et PF > 1 avec 0,6 pip de coût TOTAL supplémentaire par trade
       (≈ commission d'un compte à spread brut + glissement au fix ; le spread Dukascopy est déjà déduit).
- FAIL aussi si clairement instable : moins de 2 trimestres sur 4 positifs.
- INCONCLUSIVE sinon (positif mais trop faible, trop concentré, non spécifique ou trop sensible aux coûts).
Règles renforcées le 1er octobre 2026 à la demande de l'utilisateur, toujours AVANT d'avoir les données.
Dernier verrou (IC 95 % par jour, trimestres) le 1er octobre 2026, 11:31 Paris. Plus aucun critère ne sera ajouté.

Usage : python -m research.v4.oos_check            (données verrouillées)
        python -m research.v4.oos_check --dry-run  (essai du code sur les données de recherche déjà vues)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .data import PAIRS, PIP
from .engine import build_ctx, by, run, signals_frame, stats
from .hypotheses import h3_fix

OUT = Path(__file__).resolve().parent / "out"
H3 = dict(mode="fade", k=0.5, days="tous")
PLACEBO = [(10, 0), (11, 0), (12, 0), (13, 0), (14, 0), (15, 0), (17, 0), (18, 0)]
COSTS = [0.0, 0.2, 0.4, 0.6, 1.0]
PRIORITY = {"EURUSD": 0, "GBPUSD": 1, "USDJPY": 2}


def fade_local(ctx, hh: int, mm: int) -> pd.DataFrame:
    """Même règle que h3_fix (fade, k = 0,5, lookback 6 M5, stop 1,5 ATR, entrée +1 min), à une autre heure de Londres."""
    b = ctx.m5
    loc = b.index.tz_convert("Europe/London")
    mins = loc.hour * 60 + loc.minute
    sig_bar = np.nonzero(mins == hh * 60 + mm - 5)[0]
    c, a = b["c"].to_numpy(), b["atr"].to_numpy()
    rows = []
    for i in sig_bar:
        if i < 6 or not np.isfinite(a[i]):
            continue
        move = c[i] - b["o"].iat[i - 5]
        if abs(move) < 0.5 * a[i]:
            continue
        rows.append((i, int(-np.sign(move)), 1.5 * a[i], np.inf))
    if not rows:
        return signals_frame(ctx, [], [], [], [])
    i, d, sd, td = map(np.array, zip(*rows))
    return signals_frame(ctx, i, d, sd, td, entry_times=b.index[i] + pd.Timedelta(minutes=6))


def day_view(t: pd.DataFrame, rng) -> dict:
    d = t.groupby("fix_day")["r"].sum()
    boots = np.array([rng.choice(d.to_numpy(), len(d)).mean() for _ in range(10000)])
    one = t.sort_values(["fix_day", "prio"]).groupby("fix_day").head(1)
    return {"days": int(len(d)), "win_days": int((d > 0).sum()), "lose_days": int((d < 0).sum()),
            "flat_days": int((d == 0).sum()), "mean_R_per_day": float(d.mean()),
            "day_ci95": [float(np.quantile(boots, .025)), float(np.quantile(boots, .975))],
            "pairs_per_day": float(t.groupby("fix_day").size().mean()),
            "one_pair_per_day": stats(one["r"]),
            "corr_pairs_same_day": corr_pairs(t)}


def corr_pairs(t):
    p = t.pivot_table(index="fix_day", columns="sym", values="r")
    c = p.corr(min_periods=20)
    return {f"{a}-{b}": round(float(c.loc[a, b]), 2) for i, a in enumerate(c.columns) for b in c.columns[i + 1:]
            if c.loc[a, b] == c.loc[a, b]}


def without(t, mask) -> dict:
    return stats(t.loc[~mask, "r"])


def main(dry=False):
    rng = np.random.default_rng(11)
    C = {s: build_ctx(s, locked=not dry) for s in PAIRS}
    t = run(C, pd.concat([h3_fix(C[s], **H3) for s in PAIRS], ignore_index=True))
    if dry:
        t = t[t["period"].isin(["V1", "V2"])]           # essai sur une période déjà vue
    tm = pd.DatetimeIndex(t["time"])
    loc = tm.tz_convert("Europe/London")
    t["fix_day"] = loc.normalize().tz_localize(None)
    t["prio"] = t["sym"].map(PRIORITY)
    # 4 trimestres de 3 mois : sept.–nov., déc.–fév., mars–mai, juin–août (pas les trimestres civils)
    m = tm.tz_convert("UTC").month
    t["quarter"] = np.select([np.isin(m, [9, 10, 11]), np.isin(m, [12, 1, 2]), np.isin(m, [3, 4, 5])],
                             ["Q1 sept-nov", "Q2 déc-fév", "Q3 mars-mai"], "Q4 juin-août")
    t["month"] = tm.tz_convert("UTC").strftime("%Y-%m")
    t["weekday"] = loc.day_name()
    t["month_end"] = (t["fix_day"] == t["fix_day"] + pd.offsets.BMonthEnd(0)).to_numpy()
    res = {"data": "recherche (essai)" if dry else "verrouillé", "first": str(tm.min()), "last": str(tm.max())}

    # 1. vérification de l'heure
    lt = loc.hour * 60 + loc.minute
    utc_h = tm.tz_convert("UTC").hour
    bst = np.array([bool(x.dst()) for x in loc])
    res["check_time"] = {"all_at_1601_london": bool((lt == 16 * 60 + 1).all()),
                         "utc_hour_when_BST": sorted(set(utc_h[bst].tolist())),
                         "utc_hour_when_GMT": sorted(set(utc_h[~bst].tolist())),
                         "n_BST": int(bst.sum()), "n_GMT": int((~bst).sum())}

    # 2. résultats
    res["global"] = stats(t["r"])
    res["pairs"] = by(t, "sym")
    res["quarters"] = by(t, "quarter")
    res["months"] = by(t, "month")
    res["weekdays"] = by(t, "weekday")

    # 3. coûts (total supplémentaire par trade, aller-retour)
    res["costs"] = {}
    for x in COSTS:
        r = t["r"] - x * t["sym"].map(PIP) / t["stop"]
        res["costs"][str(x)] = stats(r) | {"mean_pips": float((r * t["stop"] / t["sym"].map(PIP)).mean())}

    # 4. vue par jour de fix
    res["day_view"] = day_view(t, rng)

    # 5. concentration
    dsum = t.groupby("fix_day")["r"].sum()
    top5 = set(dsum.sort_values(ascending=False).index[:5])
    q = res["quarters"]
    best_q = max(q, key=lambda k: q[k]["R"]) if q else None
    best_p = max(res["pairs"], key=lambda k: res["pairs"][k]["R"]) if res["pairs"] else None
    res["concentration"] = {
        "month_end_share_R": float(t.loc[t["month_end"], "r"].sum() / t["r"].sum()) if t["r"].sum() else None,
        "top5_days_share_R": float(dsum[list(top5)].sum() / t["r"].sum()) if t["r"].sum() else None,
        "without_month_end": without(t, t["month_end"].to_numpy()),
        "without_top5_days": without(t, t["fix_day"].isin(top5).to_numpy()),
        "without_best_quarter": {"quarter": best_q} | without(t, (t["quarter"] == best_q).to_numpy()),
        "without_best_pair": {"pair": best_p} | without(t, (t["sym"] == best_p).to_numpy()),
    }

    # 6. placebo
    pl = {}
    for hh, mm in PLACEBO:
        tp = run(C, pd.concat([fade_local(C[s], hh, mm) for s in PAIRS], ignore_index=True))
        if dry:
            tp = tp[tp["period"].isin(["V1", "V2"])]
        pl[f"{hh:02d}:{mm:02d}"] = stats(tp["r"])
    res["placebo"] = pl
    # contrôle d'équivalence : la fonction placebo à 16:00 reproduit exactement H3
    t16 = run(C, pd.concat([fade_local(C[s], 16, 0) for s in PAIRS], ignore_index=True))
    if dry:
        t16 = t16[t16["period"].isin(["V1", "V2"])]
    res["placebo_equivalence_16h"] = bool(len(t16) == len(t) and np.allclose(np.sort(t16["r"]), np.sort(t["r"])))

    # verdict
    g = res["global"]
    dv = res["day_view"]
    conc = res["concentration"]
    cond = {
        "a_exp_pf": g["exp"] > 0 and g["pf"] > 1,
        "b_jour_ic95": dv["mean_R_per_day"] > 0 and dv["day_ci95"][0] > 0,
        "c_trimestres": sum(1 for v in q.values() if v["exp"] > 0) >= 3,
        "d_concentration": all((conc[k]["exp"] or -1) > 0 for k in
                               ("without_month_end", "without_top5_days", "without_best_quarter", "without_best_pair")),
        "e_une_paire": (dv["one_pair_per_day"]["exp"] or -1) > 0,
        "f_placebo": all((v["exp"] if v["exp"] == v["exp"] else -9) < g["exp"] for v in pl.values()),
        "g_couts_0_6": res["costs"]["0.6"]["exp"] > 0 and res["costs"]["0.6"]["pf"] > 1,
    }
    res["conditions"] = cond
    unstable = sum(1 for v in q.values() if v["exp"] > 0) < 2
    if not cond["a_exp_pf"] or unstable:
        res["verdict"] = "FAIL"
    elif all(cond.values()):
        res["verdict"] = "PASS"
    else:
        res["verdict"] = "INCONCLUSIVE"
    name = "oos_check_dryrun.json" if dry else "oos_check.json"
    (OUT / name).write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    t.to_pickle(OUT / ("oos_check_trades_dryrun.pkl" if dry else "oos_check_trades.pkl"))
    print(json.dumps({k: res[k] for k in ("data", "first", "last", "check_time", "global", "conditions", "verdict",
                                          "placebo_equivalence_16h")}, indent=1, default=float))


if __name__ == "__main__":
    main(dry="--dry-run" in sys.argv)
