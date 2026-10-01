"""Exécution du protocole V4.

python -m research.v4.run train   → résultats Train seulement + sélection (écrit out/selection.json)
python -m research.v4.run val     → validation des variantes sélectionnées (lit selection.json, ne change rien)
python -m research.v4.run oos     → hors-échantillon verrouillé (données data/m1_locked), une seule fois
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .data import PAIRS
from .engine import TRAIN, VAL, build_ctx, by, run, stats
from .hypotheses import grid, neighbors, vname

OUT = Path(__file__).resolve().parent / "out"


def ctxs(locked=False):
    return {s: build_ctx(s, locked) for s in PAIRS}


def trades_for(C, fn, v):
    sig = pd.concat([fn(C[s], **v) for s in C], ignore_index=True)
    return run(C, sig)


def train_criteria(t: pd.DataFrame, nb_exp: list[float], hyp: str) -> dict:
    tr = t[t["period"].isin(TRAIN)]
    s = stats(tr["r"])
    per = {p: stats(tr[tr["period"] == p]["r"])["exp"] for p in TRAIN}
    pairs = by(tr, "sym")
    pos_pairs = sum(1 for v in pairs.values() if v["exp"] > 0)
    c = {
        "1_exp_t": s["exp"] > 0 and (s["t"] or 0) >= 2.0,
        "2_n": s["n"] >= 60,
        "3_T1_T2": all((per[p] or -1) > 0 for p in TRAIN),
        "4_voisin": any(e > 0 for e in nb_exp),
        "5_sans_top5": (s["ex_top5"] or -1) > 0,
        "6_pf": s["pf"] >= 1.10,
        "7_paires": True if hyp == "H4" else pos_pairs >= 2,
    }
    return {"stats": s, "per": per, "pairs": pairs, "criteria": c, "pass": all(c.values()),
            "only_n_fails": (not c["2_n"]) and all(v for k, v in c.items() if k != "2_n")}


def stage_train():
    OUT.mkdir(exist_ok=True)
    C = ctxs()
    res, trades = {}, {}
    for hyp, (fn, variants) in grid().items():
        exps = {}
        for v in variants:
            t = trades_for(C, fn, v)
            trades[(hyp, vname(v))] = t
            exps[vname(v)] = stats(t[t["period"].isin(TRAIN)]["r"])["exp"]
        res[hyp] = []
        for v in variants:
            nb = [exps[vname(w)] for w in neighbors(variants, v)]
            ev = train_criteria(trades[(hyp, vname(v))], [x for x in nb if x == x], hyp)
            ev["variant"], ev["params"] = vname(v), v
            ev["robust_score"] = min([ev["stats"]["exp"]] + nb) if nb else ev["stats"]["exp"]
            res[hyp].append(ev)
        print(f"\n## {hyp}")
        for ev in res[hyp]:
            s = ev["stats"]
            fails = [k for k, ok in ev["criteria"].items() if not ok]
            print(f"  {ev['variant']:<55} n={s['n']:4} exp={s['exp']:+.3f} t={s['t']:+.2f} pf={s['pf']:.2f} "
                  f"T1={ev['per']['T1']:+.3f} T2={ev['per']['T2']:+.3f} {'PASS' if ev['pass'] else fails}")
    sel = {}
    for hyp, evs in res.items():
        ok = [e for e in evs if e["pass"]]
        if ok:
            best = max(ok, key=lambda e: e["robust_score"])
            sel[hyp] = {"decision": "KEEP FOR VALIDATION", "variant": best["variant"], "params": best["params"]}
        elif any(e["only_n_fails"] for e in evs):
            e = max([e for e in evs if e["only_n_fails"]], key=lambda e: e["robust_score"])
            sel[hyp] = {"decision": "RETEST (trop peu de trades)", "variant": e["variant"], "params": e["params"]}
        else:
            sel[hyp] = {"decision": "REJECT", "variant": None}
    (OUT / "train.json").write_text(json.dumps(res, indent=1, default=float))
    (OUT / "selection.json").write_text(json.dumps(sel, indent=1, ensure_ascii=False))
    pickle.dump({k: v for k, v in trades.items()}, open(OUT / "trades_all.pkl", "wb"))
    print("\nSélection :", json.dumps(sel, indent=1, ensure_ascii=False))


def stage_val():
    sel = json.loads((OUT / "selection.json").read_text())
    trades = pickle.load(open(OUT / "trades_all.pkl", "rb"))
    out = {}
    for hyp, s in sel.items():
        if s["variant"] is None:
            continue
        t = trades[(hyp, s["variant"])]
        va = t[t["period"].isin(VAL)]
        out[hyp] = {"variant": s["variant"], "decision_train": s["decision"], "VAL": stats(va["r"]),
                    "per": {p: stats(t[t["period"] == p]["r"]) for p in ("T1", "T2", "V1", "V2")},
                    "pairs_VAL": by(va, "sym")}
        v = out[hyp]
        v["candidate"] = (v["VAL"]["exp"] > 0 and v["VAL"]["pf"] > 1 and
                          all((v["per"][p]["exp"] or 0) >= 0 for p in VAL))
        print(hyp, s["variant"], json.dumps({k: round(x, 3) if isinstance(x, float) else x
                                             for k, x in v["VAL"].items()}), "→", "CANDIDATE" if v["candidate"] else "REJECT")
    (OUT / "validation.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    {"train": stage_train, "val": stage_val}[sys.argv[1]]()
