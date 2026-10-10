"""E003 — exécution : python3 experiments/E003-…/code/run.py train|validation|account

train      : 12 variantes, sélection par hypothèse, critères 1–9, placebo, test anti-look-ahead → results/train.json
validation : variantes sélectionnées qui passent TOUS les critères Train → results/validation.json
account    : partie « mise » (50 €, 1 % / 2 %) sur les variantes sélectionnées → results/account.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e003 import (PIP, VARIANTS, Data, account, lookahead_check, monte_carlo, neighbors,  # noqa: E402
                  placebo_random)
from research.common import robustness as rb  # noqa: E402

RES = HERE.parent / "results"
HYP = ("P1", "P2", "P3")


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) else ("inf" if math.isinf(f) else round(f, 5))
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def plus_cost(t, pips):
    return rb.stats(t["r"] - pips * t["sym"].map(PIP) / t["stop"])


def half(t, a, b):
    tt = pd.DatetimeIndex(t["time"])
    return rb.stats(t.loc[(tt >= pd.Timestamp(a, tz="UTC")) & (tt < pd.Timestamp(b, tz="UTC")), "r"])


def train():
    d = Data("train")
    out = {"variants": {}, "selection": {}, "warmup_days_excluded": 3}
    trades = {}
    for vid in VARIANTS:
        t = d.trades(vid)
        trades[vid] = t
        rep = rb.full_report(t, "UTC") if len(t) else {"global": rb.stats([])}
        rep["T1"] = half(t, "2025-09-01", "2025-12-01")
        rep["T2"] = half(t, "2025-12-01", "2026-03-01")
        rep["plus_0.5pip"] = plus_cost(t, 0.5)
        rep["without_top5_trades"] = rb.stats(t["r"].sort_values().iloc[:-5]) if len(t) > 5 else rb.stats([])
        rep["exits"] = t["exit"].value_counts().to_dict() if len(t) else {}
        out["variants"][vid] = rep
        g = rep["global"]
        print(f"{vid}: n={g['n']} exp={g['exp']:+.3f} t={g['t']:+.2f} pf={g['pf']:.2f}", flush=True)
    for h in HYP:
        vids = [v for v in VARIANTS if VARIANTS[v]["h"] == h]
        ex = {v: out["variants"][v]["global"]["exp"] for v in vids}
        score = {v: min([ex[v]] + [ex[n] for n in neighbors(v)]) for v in vids}
        elig = [v for v in vids if out["variants"][v]["global"]["n"] >= 60] or vids
        sel = sorted(elig, key=lambda v: (-score[v], v))[0]
        rep, t = out["variants"][sel], trades[sel]
        pl = placebo_random(d, d.sigs(sel))
        g = rep["global"]
        pairs_pos = sum(1 for s in rep["pairs"].values() if s["exp"] > 0)
        crit = {
            "1_exp_pos_t2": bool(g["exp"] > 0 and g["t"] >= 2.0), "2_n60": bool(g["n"] >= 60),
            "3_T1_T2_pos": bool(rep["T1"]["exp"] > 0 and rep["T2"]["exp"] > 0),
            "4_neighbor_pos": bool(any(ex[n] > 0 for n in neighbors(sel))),
            "5_without_top5": bool(rep["without_top5_trades"]["exp"] > 0), "6_pf_1.10": bool(g["pf"] >= 1.10),
            "7_pairs_2of3": bool(pairs_pos >= 2), "8_plus_0.5pip": bool(rep["plus_0.5pip"]["exp"] > 0),
            "9_beats_placebo_p95": bool(g["exp"] > np.quantile(pl, .95)),
        }
        out["selection"][h] = {"selected": sel, "prudent_score": score, "criteria": crit,
                               "passes_train": all(crit.values()),
                               "placebo_random_dir": {"mean": float(pl.mean()), "p95": float(np.quantile(pl, .95))},
                               "lookahead": lookahead_check(d, sel)}
        print(h, sel, "PASS" if all(crit.values()) else "FAIL", crit, flush=True)
    RES.mkdir(exist_ok=True)
    (RES / "train.json").write_text(json.dumps(clean(out), indent=1, ensure_ascii=False))


def validation():
    tr = json.loads((RES / "train.json").read_text())
    todo = {h: s["selected"] for h, s in tr["selection"].items() if s["passes_train"]}
    out = {"evaluated": todo, "note": "seules les variantes qui passent TOUS les critères Train sont évaluées"}
    if todo:
        dA, dB = Data("valA"), Data("valB")
        for h, vid in todo.items():
            a, b = dA.trades(vid), dB.trades(vid)
            ab = pd.concat([a, b])
            qB = rb.quarters(b)
            crit = {"A_exp_pf": bool(rb.stats(a["r"])["exp"] > 0 and rb.stats(a["r"])["pf"] > 1),
                    "B_exp_pf": bool(rb.stats(b["r"])["exp"] > 0 and rb.stats(b["r"])["pf"] > 1),
                    "B_3of4_quarters": bool(sum(q["exp"] >= 0 for q in qB.values()) >= 3),
                    "AB_plus_0.5pip": bool(plus_cost(ab, 0.5)["exp"] > 0)}
            out[h] = {"variant": vid, "A": rb.full_report(a), "B": rb.full_report(b), "criteria": crit,
                      "passes_validation": all(crit.values())}
    (RES / "validation.json").write_text(json.dumps(clean(out), indent=1, ensure_ascii=False))
    print(json.dumps(clean({h: out[h]["criteria"] for h in todo}), indent=1))


def account_part():
    tr = json.loads((RES / "train.json").read_text())
    sel = {h: s["selected"] for h, s in tr["selection"].items()}
    ds = [Data("valB"), Data("train"), Data("valA")]
    mid = {s: pd.concat([d.mid[s] for d in ds]).sort_index() for s in ("EURUSD", "GBPUSD", "USDJPY")}
    mid = {s: m[~m.index.duplicated()] for s, m in mid.items()}
    out = {"note": "simulation de recherche : aucun changement du Risk Manager ni de la baseline", "hyp": {}}
    for h, vid in sel.items():
        t = pd.concat([d.trades(vid) for d in ds]).sort_values("time").reset_index(drop=True)
        res = {"variant": vid, "trades_24m": int(len(t)), "exp_R_24m": float(t["r"].mean()),
               "exp_R_24m_plus_0.5pip": plus_cost(t, 0.5)["exp"]}
        for risk in (0.01, 0.02):
            for xp in (0.0, 0.5):
                acc = account(t, mid, risk, xp)
                key = f"risk_{int(risk*100)}pct_cost_+{xp}pip"
                res[key] = {**acc, "monte_carlo": monte_carlo(acc["_pnl"])}
                print(h, vid, key, {k: v for k, v in acc.items() if not k.startswith("_")}, flush=True)
            acc = account(t, mid, risk, 0.0, force_min=True)
            res[f"risk_{int(risk*100)}pct_force_0.01lot"] = acc
        out["hyp"][h] = res
    (RES / "account.json").write_text(json.dumps(clean(out), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    {"train": train, "validation": validation, "account": account_part}[sys.argv[1]]()
