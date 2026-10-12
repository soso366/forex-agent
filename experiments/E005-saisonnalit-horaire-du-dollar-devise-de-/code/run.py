"""E005 : python3 -I run.py count|train|validation  (pas d'OOS dans ce script : l'OOS n'est jamais lu ici)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e005 as e  # noqa: E402
from research.common import robustness as rb  # noqa: E402

RES = HERE.parent / "results"
COSTS = (0.0, 0.2, 0.5, 1.0)


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) else ("inf" if math.isinf(f) else round(f, 5))
    if isinstance(o, (pd.Timestamp,)) or hasattr(o, "isoformat"):
        return str(o)
    return o


def write(name, obj):
    RES.mkdir(exist_ok=True)
    (RES / name).write_text(json.dumps(clean(obj), indent=1, ensure_ascii=False))


def summary(t):
    r = rb.stats(t["r"])
    return {"trades": r, "mean_pips_net": float(t["pips"].mean()) if len(t) else None, "day": e.day_stats(t),
            "costs": {str(c): e.nets(t, c) for c in COSTS}}


def a_given_b_prev(tA, tB):
    keep = []
    for s, g in tA.groupby("sym"):
        b = tB[tB["sym"] == s].sort_values("day")
        for i, r in g.iterrows():
            prev = b[b["day"] < r["day"]]
            if len(prev) and (r["day"] - prev.iloc[-1]["day"]).days <= 4 and prev.iloc[-1]["r"] > 0:
                keep.append(i)
    return tA.loc[keep]


def count(w, pairs):
    out = {}
    for name, spec in {**e.VARIANTS, **e.SENS}.items():
        sg = e.signals(pairs, w, *spec)
        out[name] = {"n": int(len(sg)), "by_pair": sg.groupby("sym").size().to_dict()}
    out["placebo"] = {str(s): int(len(e.signals(pairs, w, s, 240, e.DIR_A))) for s in e.PLACEBO_STARTS}
    return out


def evaluate(wname, thresholds):
    w = e.WINDOWS[wname]
    pairs = {s: e.Pair(df, s) for s, df in e.load_window(wname).items()}
    V = {k: e.make(pairs, w, v) for k, v in {**e.VARIANTS, **e.SENS}.items()}
    A, B = V["A"], V["B"]
    AB = pd.concat([A, B]).sort_values("time")
    plac = {s: e.make(pairs, w, (s, 240, e.DIR_A)) for s in e.PLACEBO_STARTS}
    rep = {"window": w, "variants": {k: summary(t) for k, t in V.items()}, "A+B": summary(AB),
           "A|Bveille": summary(a_given_b_prev(A, B))}
    full = rb.full_report(A.assign(time=pd.to_datetime(A["time"], utc=True)))
    rep["A_full_report"] = full
    rep["A_no_usdjpy"] = summary(A[A["sym"] != "USDJPY"])
    rep["A_pairs"] = {s: summary(g) for s, g in A.groupby("sym")}
    rep["A_months"] = e.months(A)
    rep["A_conc"] = e.conc(A)
    rep["A_week_boot"] = e.week_boot(A)
    rep["A_day_boot"] = rb.day_view(A.assign(time=pd.to_datetime(A["time"], utc=True)))
    pm = {s: float(t["r"].mean()) for s, t in plac.items()}
    pool = sorted(list(pm.values()) + [float(A["r"].mean())], reverse=True)
    rank = 1 + pool.index(float(A["r"].mean()))
    rep["placebo"] = {"means_R": pm, "true_mean_R": float(A["r"].mean()), "rank_of_true_among_11": rank,
                      "diff_vs_mean_placebo": e.day_boot_diff(A, list(plac.values())),
                      "sign_perm_by_day": e.sign_perm_p(A)}
    rep["A_mean_by_weekday"] = {int(k): float(v) for k, v in A.groupby(pd.to_datetime(A["day"]).dt.weekday)["r"].mean().items()}
    return A, rep


def train_verdict(A, rep):
    s = rep["variants"]["A"]
    pairs_pos = sum(1 for p in rep["A_pairs"].values() if p["trades"]["exp"] > 0)
    months_pos = sum(1 for m in rep["A_months"].values() if m["exp"] > 0)
    c = {
        "1_n>=300": s["trades"]["n"] >= 300,
        "1_mean>=0.05R": s["trades"]["exp"] >= 0.05,
        "1_mean_pips_net>=0.3": (s["mean_pips_net"] or -9) >= 0.3,
        "1_day_t>=2.5": (s["day"]["t"] or -9) >= 2.5,
        "2_ci95_day_low>0": rep["A_day_boot"]["ci95"][0] > 0,
        "3_placebo_rank1_of_11": rep["placebo"]["rank_of_true_among_11"] == 1,
        "3_diff_vs_placebo_ci_low>0": rep["placebo"]["diff_vs_mean_placebo"]["ci95"][0] > 0,
        "3_sign_perm_p<=0.05": rep["placebo"]["sign_perm_by_day"]["p"] <= 0.05,
        "4_cost+0.5pip_mean>0": s["costs"]["0.5"]["exp"] > 0,
        "5_without_top5_days>0": rep["A_conc"]["without_top5_days"]["exp"] > 0,
        "5_without_worst5_days>0": rep["A_conc"]["without_worst5_days"]["exp"] > 0,
        "5_pairs_pos>=2": pairs_pos >= 2,
        "5_months_pos>=4": months_pos >= 4,
        "6_ex_usdjpy_mean>=0": rep["A_no_usdjpy"]["trades"]["exp"] >= 0,
    }
    return c


def main(mode):
    if mode == "count":
        w = e.WINDOWS["train"]
        pairs = {s: e.Pair(df, s) for s, df in e.load_window("train").items()}
        write("signal_counts.json", {"train": count(w, pairs)})
        return
    if mode == "train":
        A, rep = evaluate("train", None)
        c = train_verdict(A, rep)
        rep["criteria"] = c
        rep["passed"] = bool(all(c.values()))
        write("train.json", rep)
        if not rep["passed"]:
            write("validation.json", {"skipped": "Train échoué"})
            write("oos.json", {"skipped": "Train échoué"})
        print(json.dumps(c, indent=1), rep["passed"])
    elif mode == "validation":
        tr = json.loads((RES / "train.json").read_text())
        if not tr.get("passed"):
            raise SystemExit("Train non réussi : validation interdite")
        A, rep = evaluate("validation", None)
        m_tr = tr["variants"]["A"]["trades"]["exp"]
        s = rep["variants"]["A"]
        c = {"V_mean>0": s["trades"]["exp"] > 0, "V_mean>=50%_train": s["trades"]["exp"] >= 0.5 * m_tr,
             "V_cost+0.5pip_mean>0": s["costs"]["0.5"]["exp"] > 0}
        rep["criteria"], rep["train_mean_R"] = c, m_tr
        rep["passed"] = bool(all(c.values()))
        write("validation.json", rep)
        if not rep["passed"]:
            write("oos.json", {"skipped": "Validation échouée"})
        print(json.dumps(c, indent=1), rep["passed"])


if __name__ == "__main__":
    main(sys.argv[1])
