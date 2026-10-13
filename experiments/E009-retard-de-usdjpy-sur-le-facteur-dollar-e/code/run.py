"""E009 - python3 run.py count|train|validation  (OOS : non implemente ici, uniquement si oos-gate = OUVERT).
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
import e009 as E  # noqa: E402

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


def in_split(ev, split):
    a, b = E.SPLITS[split]
    if len(ev) == 0:
        return ev
    return ev[(ev["day"] >= pd.Timestamp(a)) & (ev["day"] < pd.Timestamp(b))].reset_index(drop=True)


def evs(D, split, vid, z=None, shift=0):
    thr, hold = E.VARIANTS[vid]
    return in_split(E.build_events(D.z if z is None else z, D.atr, thr, hold, shift_h=shift), split)


def cnt(ev):
    if len(ev) == 0:
        return dict(n=0)
    hrs = ev["hour"].value_counts().sort_index()
    sh = hrs / len(ev)
    return dict(n=int(len(ev)), days=int(ev["day"].nunique()),
                per_month=pd.Series(pd.DatetimeIndex(ev["day"]).strftime("%Y-%m")).value_counts().sort_index().to_dict(),
                per_hour_london=hrs.to_dict(), max_hour_share=float(sh.max()),
                share_13_14=float(((ev["hour"] == 13)).mean()),
                buys=int((ev["dir"] > 0).sum()), sells=int((ev["dir"] < 0).sum()),
                first=str(ev["ts"].min()), last=str(ev["ts"].max()))


def do_count(split="train"):
    D = E.Data(E.load(split))
    out = dict(experiment="E009", split=split, note="comptage AVANT tout calcul de R", variants={}, placebos={})
    out["first_z_available"] = str(D.z.index[0])
    out["z_bars"] = int(len(D.z))
    for v in E.VARIANTS:
        out["variants"][v] = cnt(evs(D, split, v))
    za = E.zscore(D.g_alone)
    out["placebos"]["usdjpy_alone"] = cnt(evs(D, split, "A", za))
    for s in E.SHIFTS:
        out["placebos"][f"shift{s:+d}h"] = cnt(evs(D, split, "A", None, s))
    out["A_n_min_ok"] = out["variants"]["A"]["n"] >= E.N_MIN
    write("signal_counts.json" if split == "train" else f"signal_counts_{split}.json", out)
    a = out["variants"]["A"]
    print(json.dumps(clean(dict(A_n=a["n"], ok=out["A_n_min_ok"], max_hour_share=a.get("max_hour_share"),
                                share_13=a.get("share_13_14"), B=out["variants"]["B"]["n"], C=out["variants"]["C"]["n"],
                                D=out["variants"]["D"]["n"], first_z=out["first_z_available"])), indent=1))


def counts_committed():
    p = RES / "signal_counts.json"
    if not p.exists():
        return False
    rel = str(p.relative_to(E.ROOT))
    tr = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=E.ROOT, capture_output=True).returncode == 0
    cl = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=E.ROOT).returncode == 0
    return tr and cl


def describe(t):
    if len(t) == 0:
        return dict(stats=rb.stats([]))
    return dict(stats=rb.stats(t["r"]), day=E.day_stats(t), costs={str(c): E.cost_stats(t, c) for c in E.COSTS},
                exits=t["exit"].value_counts().to_dict(), share_stop=float((t["exit"] == "stop").mean()))


def trades(D, split, vid, z=None, direction=+1, shift=0):
    return E.sim_events(D, evs(D, split, vid, z, shift), direction)


def perm_means(D, split, n_perm, seed=5):
    """Placebo facteur permute : usd d'un autre jour (meme heure UTC), z recalcule avec la meme procedure."""
    usd = D.usd
    key = usd.index.normalize()
    slot = ((usd.index - key) // pd.Timedelta(minutes=5)).to_numpy()
    days = key.unique()
    wk = np.array([d.weekday() < 5 for d in days])
    wdays = days[wk]
    pos = {d: i for i, d in enumerate(wdays)}
    ndays = len(wdays)
    U = np.full((ndays, 288), np.nan)
    m = np.array([k in pos for k in key])
    ri = np.array([pos[k] for k in key[m]])
    U[ri, slot[m]] = usd.to_numpy()[m]
    rj = D.r[E.SYM]
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_perm):
        p = rng.permutation(ndays)
        fix = np.nonzero(p == np.arange(ndays))[0]
        for i in fix:
            j = (i + 1) % ndays
            p[i], p[j] = p[j], p[i]
        up = np.full(len(usd), np.nan)
        up[m] = U[p[ri], slot[m]]
        g = rj - pd.Series(up, index=usd.index)
        z = E.zscore(g)
        t = E.sim_events(D, in_split(E.build_events(z, D.atr, *E.VARIANTS["A"][:1], E.VARIANTS["A"][1]), split))
        out.append(float(t["r"].mean()) if len(t) else np.nan)
    return np.array(out)


def drift_base(D, split):
    """Derive inconditionnelle : R moyen (hors spread, mouvement mid) d'un ACHAT a chaque barre M5 de la fenetre, par heure Londres."""
    thr, hold = E.VARIANTS["A"]
    a, b = E.SPLITS[split]
    acc = {}
    for L, av in D.atr.items():
        tc = L + pd.Timedelta(minutes=5)
        if not (pd.Timestamp(a, tz="UTC") <= tc < pd.Timestamp(b, tz="UTC")):
            continue
        lt = tc.tz_convert(E.LONDON)
        if not (8 <= lt.hour < 15) or lt.weekday() > 4 or not (av > 0):
            continue
        i, j = D.i1(tc), D.i1(tc) + hold - 1
        if j >= len(D.mc) or not (np.isfinite(D.mo[i]) and np.isfinite(D.mc[j])):
            continue
        acc.setdefault(lt.hour, []).append((D.mc[j] - D.mo[i]) / (E.STOP_ATR * av))
    return {h: float(np.mean(v)) for h, v in acc.items()}


def ann_flag(t):
    """Fenetre [entree-30 min ; sortie] contient 08:30 New York (= 12:30 ou 13:30 UTC selon DST US/UK, calcule explicitement)."""
    flags = []
    for ts, mn in zip(t["ts"], t["minutes"]):
        nyd = ts.tz_convert(E.NY).normalize().tz_localize(None)
        ann = pd.Timestamp(f"{nyd:%Y-%m-%d} 08:30", tz=E.NY).tz_convert("UTC")
        flags.append(bool(ts - pd.Timedelta(minutes=30) <= ann <= ts + pd.Timedelta(minutes=float(mn))))
    return np.array(flags)


def evaluate(D, split, n_perm=E.N_PERM):
    res = dict(experiment="E009", split=split)
    tA = trades(D, split, "A")
    res["A"] = describe(tA)
    res["n_signals"] = int(len(evs(D, split, "A")))
    res["A_inverse"] = describe(trades(D, split, "A", direction=-1))
    res["variants_reported"] = {v: describe(trades(D, split, v)) for v in ("B", "C", "D")}
    r = tA["r"]
    mon = pd.DatetimeIndex(tA["day"]).strftime("%Y-%m")
    mr = tA.groupby(mon)["r"].sum()
    ds = E.day_series(tA).sort_values(ascending=False)
    top5 = set(ds.index[:5])
    res["months"] = dict(R=mr.to_dict(), positive=int((mr > 0).sum()), of=int(len(mr)),
                         max_share=float(mr.max() / mr.sum()) if mr.sum() > 0 else None)
    res["without_top5_days"] = rb.stats(tA.loc[~tA["day"].isin(top5), "r"])
    res["top5_days"] = {str(k.date()): float(v) for k, v in ds.head(5).items()}
    k = max(1, int(round(0.1 * len(tA))))
    res["top10pct_trades_share"] = float(r.sort_values(ascending=False).head(k).sum() / r.sum()) if r.sum() != 0 else None
    res["tail"] = dict(worst_trade=float(r.min()), q05=float(r.quantile(.05)), share_stop=float((tA["exit"] == "stop").mean()),
                       worst_day=float(E.day_series(tA).min()))
    res["R_in_pips"] = dict(mean_stop_pips=float((tA["stop"] / E.PIP[E.SYM]).mean()),
                            median_stop_pips=float((tA["stop"] / E.PIP[E.SYM]).median()),
                            cost_half_pip_in_R=float((0.5 * E.PIP[E.SYM] / tA["stop"]).mean()))
    sp = [float(D.raw[E.SYM]["spread"].reindex([t]).iloc[0]) / E.PIP[E.SYM] for t in tA["ts"]]
    res["spread_entry_pips"] = dict(mean=float(np.nanmean(sp)), median=float(np.nanmedian(sp)))
    res["directions"] = {("buy" if d > 0 else "sell"): rb.stats(g["r"]) for d, g in tA.groupby("dir")}
    res["hours_london"] = {int(h): rb.stats(g["r"]) for h, g in tA.groupby("hour")}
    res["hour_distribution"] = cnt(evs(D, split, "A"))
    if res["hour_distribution"].get("max_hour_share", 0) > 0.35 or res["hour_distribution"].get("share_13_14", 0) > 0.35:
        zh = E.zscore_hour(D.g)
        res["diag_sigma_by_hour"] = describe(E.sim_events(D, evs(D, split, "A", zh)))
    # derive
    base = drift_base(D, split)
    adj = tA["r"] - tA["dir"] * tA["hour"].map(base)
    res["drift"] = dict(base_long_R_by_hour=base, adjusted_mean=float(adj.mean()), raw_mean=float(r.mean()))
    # annonces
    fl = ann_flag(tA)
    res["announce"] = dict(with_announce=rb.stats(tA.loc[fl, "r"]), without_announce=rb.stats(tA.loc[~fl, "r"]), share_with=float(fl.mean()))
    first_fri = []
    for ts in tA["ts"]:
        d = ts.tz_convert(E.LONDON).tz_localize(None).normalize()
        mon_ = d - pd.Timedelta(days=d.weekday())
        fri = mon_ + pd.Timedelta(days=4)
        first_fri.append(fri.day <= 7)
    ff = np.array(first_fri)
    res["nfp_weeks"] = dict(nfp=rb.stats(tA.loc[ff, "r"]), other=rb.stats(tA.loc[~ff, "r"]))
    # placebos
    za = E.zscore(D.g_alone)
    res["placebo_usdjpy_alone"] = describe(E.sim_events(D, evs(D, split, "A", za)))
    plc = {}
    for s in E.SHIFTS:
        t = trades(D, split, "A", shift=s)
        plc[f"{s:+d}h"] = rb.stats(t["r"]) if len(t) else rb.stats([])
    res["placebo_hours"] = plc
    mA = res["A"]["stats"]["exp"]
    res["placebo_hours_rank"] = int(1 + sum(1 for v in plc.values() if v["exp"] == v["exp"] and v["exp"] >= mA))
    pm = perm_means(D, split, n_perm)
    pm = pm[np.isfinite(pm)]
    res["placebo_permuted"] = dict(n=int(len(pm)), mean=float(pm.mean()), q90=float(np.quantile(pm, .90)),
                                   q95=float(np.quantile(pm, .95)), real=mA,
                                   p=float((1 + (pm >= mA).sum()) / (len(pm) + 1)))
    res["one_per_day"] = rb.one_per_day(tA)
    res["full_report"] = rb.full_report(tA)
    tA[["day", "ts", "z", "hour", "dir", "r", "stop", "exit", "minutes"]].to_csv(RES / f"trades_{split}.csv", index=False)
    return res


def judge_train(res):
    a, d = res["A"], res["A"]["day"]
    mA = a["stats"]["exp"]
    c = {}
    c["1_n_ge_150"] = a["stats"]["n"] >= E.N_MIN
    c["1_mean_ge_0.05"] = mA >= 0.05
    c["1_t_day_ge_2"] = bool(d["t"] is not None and d["t"] == d["t"] and d["t"] >= 2.0)
    c["2_ci_low_gt_0"] = bool(d["ci95"][0] == d["ci95"][0] and d["ci95"][0] > 0)
    al = res["placebo_usdjpy_alone"]["stats"]["exp"]
    c["3_beats_usdjpy_alone_by_0.03"] = bool(al != al or mA - al > 0.03)
    c["3_permuted_ge_q95"] = mA >= res["placebo_permuted"]["q95"]
    c["3_hours_rank1_of_13"] = res["placebo_hours_rank"] == 1
    c["4_cost_0.5_ge_0"] = a["costs"]["0.5"]["exp"] >= 0
    c["5_wo_top5_gt_0"] = res["without_top5_days"]["exp"] > 0
    c["5_months_ge_4of6"] = res["months"]["positive"] >= 4
    ms = res["months"]["max_share"]
    c["5_no_month_gt_25pct"] = bool(ms is not None and ms <= 0.25)
    c["7_drift_adjusted_ge_0.03"] = res["drift"]["adjusted_mean"] >= 0.03
    wo = res["announce"]["without_announce"]
    c["6_without_announce_gt_0"] = bool(wo["n"] > 0 and wo["exp"] > 0)
    return c


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "count":
        do_count("train")
    elif mode == "train":
        assert counts_committed(), "signal_counts.json non commite"
        D = E.Data(E.load("train"))
        res = evaluate(D, "train")
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
        D = E.Data(E.load("validation"))
        res = evaluate(D, "validation")
        a = res["A"]["stats"]["exp"]
        res["criteria"] = {"mean_gt_0": a > 0, "ge_50pct_train": a >= 0.5 * tr["A"]["stats"]["exp"],
                           "cost_0.5_ge_0": res["A"]["costs"]["0.5"]["exp"] >= 0,
                           "inverse_negative": res["A_inverse"]["stats"]["exp"] < 0}
        res["passed"] = all(res["criteria"].values())
        write("validation.json", res)
        print(json.dumps(clean(res["criteria"])))
