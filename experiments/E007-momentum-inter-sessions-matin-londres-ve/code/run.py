"""E007 - python3 run.py count|train|validation  (OOS : non implémenté, seulement si oos-gate = OUVERT).
count : comptage des signaux, AUCUN R -> results/signal_counts.json ; train : critères du protocole -> results/train.json."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e007 as E  # noqa: E402

RES = HERE.parent / "results"
rb = E.rb


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
    return o


def write(name, obj):
    RES.mkdir(exist_ok=True)
    (RES / name).write_text(json.dumps(clean(obj), indent=1, ensure_ascii=False))


def build(split):
    raw = E.load_window(split)
    return {s: E.Pair(raw[s], s) for s in E.PAIRS}, E.WINDOWS[split]


def mean(t):
    return float(t["r"].mean()) if len(t) else float("nan")


def do_count(split="train"):
    P, w = build(split)
    out = dict(experiment="E007", split=split, note="comptage AVANT tout calcul de R", variants={}, placebo_shifts={})
    for v in E.VARIANTS:
        sg = E.signals(P, w, v)
        out["variants"][v] = dict(n=int(len(sg)), per_pair=sg.groupby("sym").size().to_dict() if len(sg) else {},
                                  days=int(sg["day"].nunique()) if len(sg) else 0,
                                  per_month=pd.Series(pd.to_datetime(sg["day"]).dt.strftime("%Y-%m")).value_counts().sort_index().to_dict() if len(sg) else {})
    for k in E.SHIFTS:
        out["placebo_shifts"][str(k)] = int(len(E.signals(P, w, "A", k)))
    out["A_n_min_ok"] = out["variants"]["A"]["n"] >= 300
    write("signal_counts.json", out)
    print(json.dumps(clean(out["variants"]), ensure_ascii=False)[:600], out["A_n_min_ok"])


def do_train():
    P, w = build("train")
    A = E.trades(P, w, "A")
    r = {"experiment": "E007", "split": "train", "variant_A": {}, "criteria": {}}
    g = rb.stats(A["r"]); ds = E.day_stats(A); dv = rb.day_view(A)
    r["variant_A"] = dict(stats=g, day_stats=ds, day_view=dv, exit_share=A["exit"].value_counts(normalize=True).to_dict(),
                          mean_pips=float(A["pips"].mean()), full_report=rb.full_report(A))
    c = {}
    c["1_n_mean_t"] = dict(n=g["n"], mean=g["exp"], t_day=ds["t"], ok=bool(g["n"] >= 300 and g["exp"] >= 0.05 and ds["t"] >= 2.0))
    c["2_ci_day"] = dict(ci95=dv["ci95"], ok=bool(dv["ci95"][0] > 0))
    plac = {k: mean(E.trades(P, w, "A", k)) for k in E.SHIFTS}
    plac = {k: v for k, v in plac.items() if not math.isnan(v)}
    allm = sorted(list(plac.values()) + [g["exp"]], reverse=True)
    rank = allm.index(g["exp"]) + 1
    fade = E.trades(P, w, "A", 0, True)
    c["3_placebo"] = dict(placebos=plac, rank=rank, n_windows=len(allm), rank_max=math.ceil(0.1 * len(allm)),
                          fade_mean=mean(fade), ok=bool(rank <= math.ceil(0.1 * len(allm)) and mean(fade) < 0))
    c5 = rb.costs(A, (0.5,))["0.5"]
    c["4_cost05"] = dict(mean=c5["exp"], ok=bool(c5["exp"] >= 0))
    day = pd.DatetimeIndex(A["time"]).tz_convert("UTC").normalize().tz_localize(None)
    top5 = set(A.assign(_d=day).groupby("_d")["r"].sum().sort_values(ascending=False).index[:5])
    wo5 = mean(A[~pd.Series(day).isin(top5).values])
    pm = {s: mean(x) for s, x in A.groupby("sym")}
    mo = A.assign(_m=pd.to_datetime(A["day"]).dt.strftime("%Y-%m")).groupby("_m")["r"].mean()
    c["5_concentration"] = dict(without_top5=wo5, pairs=pm, months=mo.to_dict(),
                                ok=bool(wo5 > 0 and sum(v > 0 for v in pm.values()) >= 2 and (mo > 0).sum() >= 4))
    usd = A["dir"] * A["sym"].map(E.USD_SIGN)
    ul, us = mean(A[usd > 0]), mean(A[usd < 0])
    c["6_usd_sign"] = dict(usd_long=ul, usd_short=us, n_long=int((usd > 0).sum()), n_short=int((usd < 0).sum()),
                           ok=bool(ul >= 0 and us >= 0))
    ds_ = A["day"].astype(str)
    nf = pd.to_datetime(A["day"]).map(lambda d: d.weekday() == 4 and d.day <= 7) | ds_.isin(E.FOMC)
    c["7_no_nfp_fomc"] = dict(mean=mean(A[~nf.values]), n=int((~nf).sum()), ok=bool(mean(A[~nf.values]) > 0))
    c["8_no_dst_week"] = dict(mean=mean(A[~ds_.isin(E.DST_DAYS).values]), ok=bool(mean(A[~ds_.isin(E.DST_DAYS).values]) > 0))
    fl, fs = mean(E.simulate_trades(P, E.fixed_usd(P, w, +1))), mean(E.simulate_trades(P, E.fixed_usd(P, w, -1)))
    c["9_control_E005"] = dict(fixed_usd_long=fl, fixed_usd_short=fs, ok=bool(g["exp"] > max(fl, fs)))
    r["criteria"] = c
    r["descriptive_variants"] = {v: dict(stats=rb.stats(t["r"]), day_stats=E.day_stats(t)) for v in ("B", "C", "D")
                                 for t in [E.trades(P, w, v)]}
    r["passed"] = bool(all(x["ok"] for x in c.values()))
    r["failed"] = [k for k, x in c.items() if not x["ok"]]
    write("train.json", r)
    print(json.dumps(clean({k: {kk: vv for kk, vv in x.items() if kk in ("ok", "mean", "n", "t_day", "rank", "n_windows")} for k, x in c.items()}), ensure_ascii=False))
    print("passed", r["passed"], r["failed"])


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "count":
        do_count()
    elif m == "train":
        do_train()
    else:
        raise SystemExit("validation/OOS : non lancé ici")
