"""E008 - python3 run.py count|train|validation  (OOS : non implemente ici, uniquement si oos-gate = OUVERT).
count : signaux (aucun R) -> results/signal_counts.json, a commiter avant train.
train : refuse si signal_counts.json non commite ; criteres du protocole -> results/train.json"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e008 as E  # noqa: E402

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
    raw = E.load(split)
    P = {s: E.Pair(raw[s], s) for s in E.PAIRS}
    a, b = E.SPLITS[split]
    hours = sorted({13 + s for s in E.SHIFTS} | {12, 13})
    ev = {h: {s: P[s].events(h, a, b) for s in E.PAIRS} for h in hours}
    return P, ev


def cnt(parts):
    df = pd.concat([p for p in parts.values() if len(p)]) if any(len(p) for p in parts.values()) else pd.DataFrame()
    if df.empty:
        return dict(n=0)
    mo = pd.DatetimeIndex(df["day"]).strftime("%Y-%m")
    return dict(n=int(len(df)), per_pair={s: int(len(p)) for s, p in parts.items()}, days=int(df["day"].nunique()),
                per_month=pd.Series(mo).value_counts().sort_index().to_dict(),
                dst_summer=int(df["utc1"].sum()), dst_winter=int((~df["utc1"]).sum()))


def sel(ev, vid):
    h, thr, hold = E.VARIANTS[vid]
    return {s: E.select(ev[h][s], thr) for s in E.PAIRS}


def do_count(split="train"):
    P, ev = build(split)
    out = dict(experiment="E008", split=split, note="comptage AVANT tout calcul de R", variants={}, placebos={})
    for v in E.VARIANTS:
        out["variants"][v] = cnt(sel(ev, v))
    for s in E.SHIFTS:
        out["placebos"][f"shift{s:+d}h"] = cnt({k: E.select(ev[13 + s][k], 0.30) for k in E.PAIRS})
    out["pair_days_13h"] = int(sum(len(ev[13][s]) for s in E.PAIRS))
    out["A_n_min_ok"] = out["variants"]["A"]["n"] >= E.N_MIN
    write("signal_counts.json" if split == "train" else f"signal_counts_{split}.json", out)
    print(json.dumps(clean({"A": out["variants"]["A"], "pair_days": out["pair_days_13h"], "ok": out["A_n_min_ok"],
                            "B": out["variants"]["B"]["n"]}), indent=1))


def counts_committed():
    p = RES / "signal_counts.json"
    if not p.exists():
        return False
    rel = str(p.relative_to(E.ROOT))
    tr = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=E.ROOT, capture_output=True).returncode == 0
    cl = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=E.ROOT).returncode == 0
    return tr and cl


def trades(P, ev, vid, direction=+1):
    h, thr, hold = E.VARIANTS[vid]
    parts = [E.sim_events(P[s], E.select(ev[h][s], thr), hold, direction) for s in E.PAIRS]
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def describe(t):
    if len(t) == 0:
        return dict(stats=rb.stats([]))
    return dict(stats=rb.stats(t["r"]), day=E.day_stats(t), costs={str(c): E.cost_stats(t, c) for c in E.COSTS},
                exits=t["exit"].value_counts().to_dict(), share_stop=float((t["exit"] == "stop").mean()))


def evaluate(split):
    P, ev = build(split)
    tA = trades(P, ev, "A")
    res = dict(experiment="E008", split=split)
    res["n_signals"] = int(sum(len(E.select(ev[13][s], 0.30)) for s in E.PAIRS))
    res["A"] = describe(tA)
    res["A_inverse"] = describe(trades(P, ev, "A", -1))
    res["variants_reported"] = {v: describe(trades(P, ev, v)) for v in ("B", "C", "D")}
    t = tA.assign(time=pd.to_datetime(tA["time"], utc=True))
    mon = pd.DatetimeIndex(t["day"]).strftime("%Y-%m")
    mr = t.groupby(mon)["r"].sum()
    ds = E.day_series(t).sort_values(ascending=False)
    top5 = set(ds.index[:5])
    ds_all = E.day_series(t)
    res["months"] = dict(R=mr.to_dict(), positive=int((mr > 0).sum()), of=int(len(mr)))
    res["pairs"] = {k: rb.stats(g["r"]) for k, g in t.groupby("sym")}
    res["without_top5_days"] = rb.stats(t.loc[~t["day"].isin(top5), "r"])
    res["top5_days"] = {str(k.date()): float(v) for k, v in ds.head(5).items()}
    r = t["r"]
    res["tail"] = dict(worst_trade=float(r.min()), q05=float(r.quantile(.05)),
                       worst_day=float(ds_all.min()), worst_day_date=str(ds_all.idxmin().date()),
                       share_stop=float((t["exit"] == "stop").mean()))
    res["dst"] = {"summer_BST": rb.stats(t.loc[t["utc1"], "r"]), "winter_GMT": rb.stats(t.loc[~t["utc1"], "r"])}
    res["one_per_day"] = rb.one_per_day(t.assign(time=t["time"]))
    res["full_report"] = rb.full_report(t.assign(time=t["time"]))
    # jours d'annonce US (rapport) : jours ou l'ADR consomme est > 1 (M >= 1) comme proxy ? non : on rapporte par |M| tranche
    res["by_absM"] = {k: rb.stats(g["r"]) for k, g in t.assign(b=pd.cut(t["M"].abs(), [0.3, 0.45, 0.6, 99])).groupby("b", observed=True)}
    # placebo horaire
    plc = {}
    for s in E.SHIFTS:
        p = [E.sim_events(P[k], E.select(ev[13 + s][k], 0.30), 240, +1, cap=True) for k in E.PAIRS]
        p = [x for x in p if len(x)]
        d = pd.concat(p, ignore_index=True) if p else pd.DataFrame()
        plc[f"{s:+d}h"] = rb.stats(d["r"]) if len(d) else rb.stats([])
    res["placebo_hours"] = plc
    mA = res["A"]["stats"]["exp"]
    res["placebo_hours_rank"] = int(1 + sum(1 for v in plc.values() if v["exp"] >= mA))
    # jours aleatoires
    rng = np.random.default_rng(7)
    allt = {k: E.sim_events(P[k], ev[13][k], 240, +1) for k in E.PAIRS}
    nreal = {k: int((tA["sym"] == k).sum()) for k in E.PAIRS}
    sims = np.empty(E.N_RAND)
    for i in range(E.N_RAND):
        v = np.concatenate([rng.choice(allt[k]["r"].to_numpy(), nreal[k], replace=False) for k in E.PAIRS if nreal[k] > 0])
        sims[i] = v.mean()
    res["random_days"] = dict(real=mA, perm_mean=float(sims.mean()), q95=float(np.quantile(sims, .95)),
                              p=float((1 + (sims >= mA).sum()) / (E.N_RAND + 1)), n_pool={k: len(v) for k, v in allt.items()})
    # E007
    e7 = list((E.ROOT / "experiments").glob("E007*/results/trades*"))
    res["corr_E007"] = "E007 absent : aucune serie de trades disponible" if not e7 else "fichiers E007: " + ", ".join(map(str, e7))
    tA[["day", "sym", "M", "r", "stop", "exit", "dir"]].assign(time=t["time"].astype(str)).to_csv(RES / f"trades_{split}.csv", index=False)
    return res, tA


def judge_train(res):
    a, d = res["A"], res["A"]["day"]
    c = {}
    c["1_n_ge_150"] = res["A"]["stats"]["n"] >= E.N_MIN
    c["1_mean_ge_0.05"] = a["stats"]["exp"] >= 0.05
    c["1_t_day_ge_2"] = bool(d["t"] is not None and d["t"] >= 2.0)
    c["2_ci_low_gt_0"] = d["ci95"][0] > 0
    c["3a_hours_rank1"] = res["placebo_hours_rank"] == 1
    c["3b_random_days_p"] = res["random_days"]["p"] <= 0.05
    c["3c_inverse_negative"] = res["A_inverse"]["stats"]["exp"] < 0
    c["4_cost_0.5_ge_0"] = a["costs"]["0.5"]["exp"] >= 0
    c["5_wo_top5_gt_0"] = res["without_top5_days"]["exp"] > 0
    c["5_pairs_ge_2of3"] = sum(1 for v in res["pairs"].values() if v["exp"] > 0) >= 2
    c["5_months_ge_4of6"] = res["months"]["positive"] >= 4
    return c


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "count":
        do_count("train")
    elif mode == "train":
        assert counts_committed(), "signal_counts.json non commite"
        res, _ = evaluate("train")
        c = judge_train(res)
        res["criteria"] = c
        res["inconclusive"] = not c["1_n_ge_150"]
        res["passed"] = all(c.values())
        write("train.json", res)
        print(json.dumps(clean({"passed": res["passed"], "criteria": c, "n": res["A"]["stats"]["n"],
                                "exp": res["A"]["stats"]["exp"], "day": res["A"]["day"]}), indent=1))
    elif mode == "validation":
        tr = json.loads((RES / "train.json").read_text())
        assert tr.get("passed") is True, "validation interdite : Train non reussi"
        res, _ = evaluate("validation")
        a = res["A"]["stats"]["exp"]
        res["criteria"] = {"mean_gt_0": a > 0, "ge_50pct_train": a >= 0.5 * tr["A"]["stats"]["exp"],
                           "cost_0.5_ge_0": res["A"]["costs"]["0.5"]["exp"] >= 0,
                           "inverse_negative": res["A_inverse"]["stats"]["exp"] < 0}
        res["passed"] = all(res["criteria"].values())
        write("validation.json", res)
        print(json.dumps(clean(res["criteria"])))
