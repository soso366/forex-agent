"""Router V4 : matrice de contexte avec abstention.

Cellule = combinaison stratégie × régime × séance × volatilité × paire (ou un sous-ensemble de ces dimensions).
Statut : EDGE (n ≥ 30 et borne basse IC90 bootstrap > 0) · NO_EDGE (n ≥ 30 et borne haute < 0) · UNKNOWN sinon.
Par défaut, UNKNOWN = NO TRADE. La matrice n'est utilisée pour filtrer que si elle est PERSISTANTE
(cellules Train et Validation de même signe, corrélation de rang positive).
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

MIN_N = 30
OUT = Path(__file__).resolve().parent / "out"


def ci90(r: np.ndarray, rng) -> tuple[float, float]:
    b = rng.choice(r, (2000, len(r))).mean(axis=1)
    return float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95))


def matrix(t: pd.DataFrame, dims: list[str], rcol="r") -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    for key, g in t.groupby(dims, observed=True):
        r = g[rcol].to_numpy(float)
        key = key if isinstance(key, tuple) else (key,)
        lo, hi = ci90(r, rng) if len(r) >= 5 else (np.nan, np.nan)
        status = "UNKNOWN"
        if len(r) >= MIN_N and lo > 0:
            status = "EDGE"
        elif len(r) >= MIN_N and hi < 0:
            status = "NO_EDGE"
        rows.append(dict(zip(dims, key)) | {"n": len(r), "exp": r.mean(), "ci_lo": lo, "ci_hi": hi, "status": status})
    return pd.DataFrame(rows)


def persistence(t: pd.DataFrame, dims: list[str], a=("T1", "T2"), b=("V1", "V2"), rcol="r", min_n=10) -> dict:
    A = t[t["period"].isin(a)].groupby(dims, observed=True)[rcol].agg(["mean", "size"])
    B = t[t["period"].isin(b)].groupby(dims, observed=True)[rcol].agg(["mean", "size"])
    m = A.join(B, lsuffix="_a", rsuffix="_b", how="inner")
    m = m[(m["size_a"] >= min_n) & (m["size_b"] >= min_n)]
    if len(m) < 3:
        return {"cells": len(m), "rank_corr": None, "same_sign": None}
    return {"cells": int(len(m)), "rank_corr": round(float(m["mean_a"].corr(m["mean_b"], method="spearman")), 2),
            "same_sign": round(float((np.sign(m["mean_a"]) == np.sign(m["mean_b"])).mean()), 2)}


def report(t: pd.DataFrame, name: str, strat_col: str | None, a, b, rcol="r") -> dict:
    base = [strat_col] if strat_col else []
    ctx_dims = ["regime", "session", "vol", "sym"]
    out = {"name": name, "full": {}, "two_dims": [], "persistence": []}
    full = matrix(t, base + ctx_dims, rcol)
    out["full"] = {"cells": len(full), "status": full["status"].value_counts().to_dict(),
                   "median_n": float(full["n"].median()) if len(full) else 0}
    for d in ctx_dims:
        m = matrix(t, base + [d], rcol)
        out["two_dims"].append({"dims": base + [d], "table": m.round(3).to_dict("records")})
        out["persistence"].append({"dims": " × ".join(base + [d])} | persistence(t, base + [d], a, b, rcol))
    for d1, d2 in itertools.combinations(ctx_dims, 2):
        out["persistence"].append({"dims": " × ".join(base + [d1, d2])} | persistence(t, base + [d1, d2], a, b, rcol))
    return out


def main():
    OUT.mkdir(exist_ok=True)
    v2 = pd.read_pickle(OUT / "v2_trades_enriched.pkl")
    v2 = v2.rename(columns={"symbol": "sym", "vol_bucket": "vol", "r_multiple": "r"})
    v2["vol"] = v2["vol"].astype(str)
    v2["P"] = np.where(v2["period"].str.startswith("P1"), "P1", "P2")
    r_v2 = report(v2.assign(period=v2["P"]), "Stratégies V2 (12 mois)", "strategy", ("P1",), ("P2",))
    h3 = pd.read_pickle(OUT / "h3_trades.pkl")
    r_h3 = report(h3, "H3 fix de Londres", None, ("T1", "T2"), ("V1", "V2"))
    res = {"V2": r_v2, "H3": r_h3}
    (OUT / "router.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    for k, r in res.items():
        print(f"\n## {r['name']}\nmatrice complète (5 dimensions) : {r['full']}")
        print(pd.DataFrame(r["persistence"]).to_string(index=False))
        for td in r["two_dims"]:
            df = pd.DataFrame(td["table"])
            print(df[df["n"] >= 10].to_string(index=False))


if __name__ == "__main__":
    main()
