"""E006 — python3 run.py count|train|validation  (OOS : non implémenté ici, uniquement si oos-gate = OUVERT).
count : signaux par paire/mois pour V1..V6, diagnostics et placebos, AUCUN R -> results/signal_counts.json (à commiter avant train)
train : refuse si signal_counts.json non commité ; critères du protocole -> results/train.json
validation : seulement si train.json passed=true -> results/validation.json"""
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
import e006 as E  # noqa: E402

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
    ev = {w: {s: P[s].events(w, a, b) for s in E.PAIRS} for w in E.WINDOWS}
    return P, ev


def variant_events(ev, vid):
    w, zmin, hold, spc, dr, pairs = E.VARIANTS[vid]
    return {s: E.select(ev[w][s], zmin, spc) for s in pairs}


def cnt(parts):
    df = pd.concat([p for p in parts.values() if len(p)]) if any(len(p) for p in parts.values()) else pd.DataFrame()
    if df.empty:
        return dict(n=0)
    mo = pd.DatetimeIndex(df["day"]).strftime("%Y-%m")
    return dict(n=int(len(df)), per_pair={s: int(len(p)) for s, p in parts.items()},
                days=int(df["day"].nunique()), per_month=pd.Series(mo).value_counts().sort_index().to_dict(),
                utc1=int(df["utc1"].sum()), utc0=int((~df["utc1"]).sum()),
                days_all=int(sum(len(ev) for ev in parts.values())))


def do_count(split="train"):
    P, ev = build(split)
    out = dict(experiment="E006", split=split, note="comptage AVANT tout calcul de R", variants={}, placebos={}, grad={})
    for vid in E.VARIANTS:
        out["variants"][vid] = cnt(variant_events(ev, vid))
    for w in E.WINDOWS:
        if w != "main":
            out["placebos"][w] = cnt({s: E.select(ev[w][s], 1.0, False) for s in E.MAIN_PAIRS})
    for z in E.DIAG_Z:
        out["grad"][f"z>={z}"] = cnt({s: E.select(ev["main"][s], z, False) for s in E.MAIN_PAIRS})
    out["grad"]["1.0<=z<1.5"] = cnt({s: E.select(ev["main"][s], 1.0, False, 1.5) for s in E.MAIN_PAIRS})
    out["pair_days_main_pairs"] = int(sum(len(ev["main"][s]) for s in E.MAIN_PAIRS))
    out["V1_n_min_ok"] = out["variants"]["V1"]["n"] >= E.N_MIN
    write("signal_counts.json" if split == "train" else f"signal_counts_{split}.json", out)
    print(json.dumps(clean({"V1": out["variants"]["V1"], "pair_days": out["pair_days_main_pairs"],
                            "ok": out["V1_n_min_ok"]}), indent=1))


def counts_committed():
    p = RES / "signal_counts.json"
    if not p.exists():
        return False
    rel = str(p.relative_to(E.ROOT))
    tr = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=E.ROOT, capture_output=True).returncode == 0
    cl = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=E.ROOT).returncode == 0
    return tr and cl


def trades_of(P, ev, vid, direction=None):
    w, zmin, hold, spc, dr, pairs = E.VARIANTS[vid]
    d = dr if direction is None else direction
    parts = [E.sim_events(P[s], E.select(ev[w][s], zmin, spc), hold, d) for s in pairs]
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def describe(t, full=True):
    if len(t) == 0:
        return dict(stats=rb.stats([]))
    out = dict(stats=rb.stats(t["r"]), day=E.day_stats(t), costs={str(c): E.cost_stats(t, c) for c in E.COSTS},
               exits=t["exit"].value_counts().to_dict(), share_stop=float((t["exit"] == "stop").mean()),
               minutes_max=float(t["minutes"].max()))
    if not full:
        return out
    t = t.assign(time=pd.to_datetime(t["time"], utc=True))
    mon = pd.DatetimeIndex(t["day"]).strftime("%Y-%m")
    mr = t.groupby(mon)["r"].sum()
    ds = E.day_series(t).sort_values(ascending=False)
    top5 = set(ds.index[:5])
    wd = pd.DatetimeIndex(t["day"]).weekday
    first_fri = (pd.DatetimeIndex(t["day"]).weekday == 4) & (pd.DatetimeIndex(t["day"]).day <= 7)
    out.update(
        pairs={k: rb.stats(g["r"]) for k, g in t.groupby("sym")},
        months_R=mr.to_dict(), months_positive=int((mr > 0).sum()), months_total=int(len(mr)),
        without_top5_days=rb.stats(t.loc[~t["day"].isin(top5), "r"]),
        top5_days=[str(x.date()) for x in top5],
        weekday={str(k): rb.stats(t.loc[wd == k, "r"]) for k in range(5)},
        monday_excluded=rb.stats(t.loc[wd != 0, "r"]),
        nfp_first_friday=rb.stats(t.loc[first_fri, "r"]), without_nfp=rb.stats(t.loc[~first_fri, "r"]),
        fomc="non daté dans le dépôt : non testé",
        dst={"UTC+0 (hiver)": rb.stats(t.loc[~t["utc1"], "r"]), "UTC+1 (été)": rb.stats(t.loc[t["utc1"], "r"])},
        sweep={"sweep": rb.stats(t.loc[t["sweep"], "r"]), "no_sweep": rb.stats(t.loc[~t["sweep"], "r"])},
        reentry={"reentry": rb.stats(t.loc[t["reentry"], "r"]), "no_reentry": rb.stats(t.loc[~t["reentry"], "r"])},
        one_per_day=rb.one_per_day(t.assign(time=t["time"]), tz="UTC"), quarters=rb.quarters(t))
    return out


def main_results(split, P, ev):
    res = {}
    t1 = trades_of(P, ev, "V1")
    res["V1"] = describe(t1)
    for vid in ("V2", "V3", "V4", "V5", "V6"):
        res[vid] = describe(trades_of(P, ev, vid), full=False)
    res["V7_continuation"] = describe(trades_of(P, ev, "V1", direction=-1), full=False)
    # placebos temporels (z>=1, 240 min, mêmes paires)
    res["placebo_windows"] = {}
    for w in E.WINDOWS:
        if w == "main":
            continue
        tt = pd.concat([E.sim_events(P[s], E.select(ev[w][s], 1.0, False), 240, +1) for s in E.MAIN_PAIRS], ignore_index=True)
        res["placebo_windows"][w] = describe(tt, full=False)
    evs = {s: (P[s], E.select(ev["main"][s], 1.0, False)) for s in E.MAIN_PAIRS}
    res["placebo_perm"] = E.perm_test(evs, 240)
    # gradient et voisins (diagnostics)
    lo = pd.concat([E.sim_events(P[s], E.select(ev["main"][s], 1.0, False, 1.5), 240) for s in E.MAIN_PAIRS], ignore_index=True)
    hi = pd.concat([E.sim_events(P[s], E.select(ev["main"][s], 1.5, False), 240) for s in E.MAIN_PAIRS], ignore_index=True)
    res["gradient"] = {"1.0<=z<1.5": rb.stats(lo["r"]), "z>=1.5": rb.stats(hi["r"])}
    res["neighbours"] = {f"z>={z}|{h}min": rb.stats(pd.concat(
        [E.sim_events(P[s], E.select(ev["main"][s], z, False), h) for s in E.MAIN_PAIRS], ignore_index=True)["r"])
        for z in E.DIAG_Z for h in E.DIAG_HOLD}
    return res, t1


def do_train():
    if not counts_committed():
        raise SystemExit("signal_counts.json non commité : lancer `count`, le commiter, puis `train`.")
    cnts = json.loads((RES / "signal_counts.json").read_text())
    n_ok = cnts["variants"]["V1"]["n"] >= E.N_MIN
    P, ev = build("train")
    res, t1 = main_results("train", P, ev)
    v1 = res["V1"]
    c = {}
    c["1_n>=150"] = n_ok
    c["1_mean>=+0.05R"] = bool(len(t1) and v1["stats"]["exp"] >= 0.05)
    c["1_day_t>=2.0"] = bool(len(t1) and (v1["day"]["t"] or 0) >= 2.0)
    c["2_ci95_low>0"] = bool(len(t1) and v1["day"]["ci95"][0] > 0)
    plw = [v["stats"]["exp"] for v in res["placebo_windows"].values() if v["stats"]["n"]]
    c["3_dominates_placebo_windows"] = bool(len(t1) and all(v1["stats"]["exp"] > x for x in plw))
    c["3_perm_p<=0.05"] = bool(res["placebo_perm"].get("p", 1) <= 0.05)
    g = res["gradient"]
    c["4_gradient"] = bool(g["z>=1.5"]["n"] >= 20 and g["z>=1.5"]["exp"] >= g["1.0<=z<1.5"]["exp"])
    c["5_cost0.5_mean>=0"] = bool(len(t1) and v1["costs"]["0.5"]["exp"] >= 0)
    c["5_without_top5_days>0"] = bool(len(t1) and v1["without_top5_days"]["exp"] > 0)
    c["5_months>=4of6"] = bool(len(t1) and v1["months_positive"] >= 4)
    c["6_no_sweep>0"] = bool(len(t1) and v1["sweep"]["no_sweep"]["n"] > 0 and v1["sweep"]["no_sweep"]["exp"] > 0)
    passed = all(c.values())
    out = dict(experiment="E006", split="train", n_V1_counted=cnts["variants"]["V1"]["n"],
               echantillon_insuffisant=not n_ok, criteria=c, passed=passed,
               note="si échantillon insuffisant : verdict 'échantillon insuffisant', seuil non abaissé; stats descriptives seulement",
               results=res)
    write("train.json", out)
    if not passed:
        write("validation.json", {"skipped": "Train échoué"})
        write("oos.json", {"skipped": "Train échoué"})
    print(json.dumps(clean({"n": v1["stats"], "day": v1["day"], "criteria": c, "passed": passed}), indent=1))


def do_validation():
    tr = json.loads((RES / "train.json").read_text())
    if not tr.get("passed"):
        raise SystemExit("Train non réussi : validation interdite.")
    P, ev = build("validation")
    res, t1 = main_results("validation", P, ev)
    v1 = res["V1"]
    tm = tr["results"]["V1"]["stats"]["exp"]
    c = {"same_sign_positive": bool(v1["stats"]["exp"] > 0),
         ">=50%_of_train_effect": bool(v1["stats"]["exp"] >= 0.5 * tm),
         "cost0.5_mean>=0": bool(v1["costs"]["0.5"]["exp"] >= 0),
         "no_sweep>0": bool(v1["sweep"]["no_sweep"]["exp"] > 0)}
    out = dict(experiment="E006", split="validation", criteria=c, passed=all(c.values()), results=res)
    write("validation.json", out)
    print(json.dumps(clean({"stats": v1["stats"], "day": v1["day"], "criteria": c, "passed": out["passed"]}), indent=1))


if __name__ == "__main__":
    {"count": do_count, "train": do_train, "validation": do_validation}[sys.argv[1]]()
