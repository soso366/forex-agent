"""Mesures et critères de robustesse du Parameter Lab.

Les critères sont FIXÉS AVANT de lancer les tests (voir ROBUSTNESS) et appliqués mécaniquement.
Unité principale : le R (résultat / risque initial), qui ne dépend pas de la taille du compte.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

UTC = timezone.utc
# Découpage décidé avant tout test. Seul l'in-sample sert à choisir ; la validation confirme ;
# le hors-échantillon n'est regardé qu'une fois, à la fin, pour la configuration verrouillée.
PERIODS = {
    "IS": (datetime(2026, 3, 8, tzinfo=UTC), datetime(2026, 6, 1, tzinfo=UTC)),     # mars → mai
    "VAL": (datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 8, 1, tzinfo=UTC)),    # juin → juillet
    "OOS": (datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 9, 1, tzinfo=UTC)),    # août (réservé)
}

ROBUSTNESS = {
    "min_gain_exp": 0.03,          # C1 : espérance IS améliorée d'au moins 0,03 R/trade, total R IS ≥ référence
    "plateau": True,               # C2 : les valeurs voisines de la grille font aussi mieux que la référence
    "min_trades_kept": 0.5,        # C3 : au moins 50 % des trades conservés
    "top3_robust": True,           # C4 : le gain survit au retrait des 3 plus gros gagnants
    "pairs_min": 2,                # C5 : au moins 2 paires sur 3 non dégradées
    "months_min": 2,               # C6 : au moins 2 mois IS sur 3 non dégradés
    "max_dd_worsening": 1.10,      # C7 : drawdown IS (en R) pas plus de 10 % pire
    "val_not_worse": True,         # C8 : validation (juin-juillet) non dégradée
    "winrate_trap": 0.25,          # C9 : rejeté si le gain moyen chute de plus de 25 % (on coupe les gros gagnants)
}


def with_r(trades: pd.DataFrame) -> pd.DataFrame:
    t = trades[trades["status"] == "closed"].copy() if len(trades) else trades.copy()
    if t.empty:
        return t
    t["entry_dt"] = pd.to_datetime(t["entry_time"], utc=True)
    t["month"] = t["entry_dt"].dt.strftime("%Y-%m")
    return t


def period(t: pd.DataFrame, name: str) -> pd.DataFrame:
    if t.empty:
        return t
    a, b = PERIODS[name]
    return t[(t["entry_dt"] >= a) & (t["entry_dt"] < b)]


def max_dd_r(r: pd.Series) -> float:
    if r.empty:
        return 0.0
    c = r.cumsum()
    peak = np.maximum.accumulate(np.concatenate([[0.0], c.to_numpy()]))[1:]
    return float((peak - c.to_numpy()).max())


def metrics(t: pd.DataFrame) -> dict:
    if t is None or t.empty:
        return {"n": 0, "win": np.nan, "R": 0.0, "exp": np.nan, "pf": np.nan, "dd": 0.0, "avg_win": np.nan,
                "avg_loss": np.nan, "time_exit": np.nan, "exp_ex_top3": np.nan}
    r = t["r_multiple"].astype(float)
    wins, losses = r[r > 0], r[r <= 0]
    top3 = r.sort_values(ascending=False).iloc[3:] if len(r) > 3 else r.iloc[0:0]
    return {
        "n": int(len(r)),
        "win": float((r > 0).mean()),
        "R": float(r.sum()),
        "exp": float(r.mean()),
        "pf": float(wins.sum() / -losses.sum()) if losses.sum() < 0 else np.inf,
        "dd": max_dd_r(r),
        "avg_win": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "time_exit": float(t["exit_reason"].str.startswith("TIME_STOP").mean()),
        "exp_ex_top3": float(top3.mean()) if len(top3) else np.nan,
        "pnl_eur": float(t["pnl_eur"].sum()),
    }


def breakdown(t: pd.DataFrame, col: str) -> dict:
    if t.empty:
        return {}
    return {k: {"n": int(len(g)), "exp": float(g["r_multiple"].mean()), "R": float(g["r_multiple"].sum())}
            for k, g in t.groupby(col)}


def paired(base: pd.DataFrame, var: pd.DataFrame) -> dict:
    """Comparaison trade par trade sur les entrées communes (utile au Bloc A : mêmes entrées, sorties différentes)."""
    key = ["symbol", "entry_time", "strategy", "direction"]
    m = base[key + ["r_multiple"]].merge(var[key + ["r_multiple"]], on=key, suffixes=("_b", "_v"))
    if m.empty:
        return {"common": 0, "diff": np.nan, "t": np.nan}
    d = m["r_multiple_v"] - m["r_multiple_b"]
    se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else np.nan
    return {"common": int(len(m)), "diff": float(d.mean()), "t": float(d.mean() / se) if se and se > 0 else np.nan}


def evaluate(base_t: pd.DataFrame, var_t: pd.DataFrame, neighbors_exp: list[float] | None = None,
             filter_block: bool = False) -> dict:
    """Applique les critères C1–C9. Renvoie les mesures, chaque critère et le verdict."""
    R = ROBUSTNESS
    b_is, v_is = period(base_t, "IS"), period(var_t, "IS")
    b_val, v_val = period(base_t, "VAL"), period(var_t, "VAL")
    mb, mv = metrics(b_is), metrics(v_is)
    mbv, mvv = metrics(b_val), metrics(v_val)
    c = {}
    c["C1_gain"] = (mv["n"] > 0 and mv["exp"] >= mb["exp"] + R["min_gain_exp"] and mv["R"] >= mb["R"])
    if neighbors_exp is None:
        c["C2_plateau"] = None
    else:
        c["C2_plateau"] = bool(neighbors_exp) and all(e is not None and not np.isnan(e) and e > mb["exp"]
                                                      for e in neighbors_exp)
    c["C3_trades"] = mv["n"] >= R["min_trades_kept"] * mb["n"]
    c["C4_top3"] = (not np.isnan(mv["exp_ex_top3"])) and mv["exp_ex_top3"] >= mb["exp_ex_top3"]
    bp, vp = breakdown(b_is, "symbol"), breakdown(v_is, "symbol")
    c["C5_pairs"] = sum(1 for s in bp if s in vp and vp[s]["R"] >= bp[s]["R"]) >= R["pairs_min"]
    bm, vm = breakdown(b_is, "month"), breakdown(v_is, "month")
    c["C6_months"] = sum(1 for m in bm if m in vm and vm[m]["R"] >= bm[m]["R"]) >= R["months_min"]
    c["C7_dd"] = mv["dd"] <= R["max_dd_worsening"] * max(mb["dd"], 1e-9)
    c["C8_val"] = mvv["n"] > 0 and (mvv["exp"] >= mbv["exp"]) and (mvv["R"] >= mbv["R"])
    c["C9_winrate_trap"] = not (mb["avg_win"] and mv["avg_win"] < (1 - R["winrate_trap"]) * mb["avg_win"]
                                and mv["exp"] - mb["exp"] < 0.05)
    tested = [v for k, v in c.items() if v is not None]
    return {"IS": mv, "IS_base": mb, "VAL": mvv, "VAL_base": mbv, "criteria": c,
            "accepted": all(tested), "paired": paired(b_is, v_is)}
