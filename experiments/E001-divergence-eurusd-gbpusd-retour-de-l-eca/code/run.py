"""E001 — exécution : python3 experiments/E001-…/code/run.py train|validation

train      : 8 variantes + contrôles C1/C2 + placebos P1/P2 + coûts + vue par jour + concentration → results/train.json
validation : variante sélectionnée uniquement, si et seulement si les critères Train passent → results/validation.json
(L'OOS n'est PAS implémenté ici : données non disponibles, lecture unique ultérieure.)
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
from e001 import (NEWS_DAYS, TZ, VARIANTS, WINDOWS, Features, control_pool, day_boot_mean,  # noqa: E402
                  load_window, make_trades, match_control, neighbors, simulate_trades)
from research.common import robustness as rb  # noqa: E402

RES = HERE.parent / "results"


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) else ("inf" if math.isinf(f) else round(f, 5))
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def evaluate(feat, f, flag, thr, H, start, end, pool=None, full=False):
    tr, info = make_trades(f, thr, start, end)
    tr = simulate_trades(feat, tr, H, early=True).dropna(subset=["r"]).reset_index(drop=True)
    out = {"info": info, "stats": rb.stats(tr["r"])}
    if len(tr) == 0:
        return out, tr
    out["exits"] = tr["exit"].value_counts().to_dict()
    out["pairs_count"] = tr["sym"].value_counts().to_dict()
    out["costs"] = rb.costs(tr)
    out["day_view"] = rb.day_view(tr, TZ)
    out["one_per_day"] = rb.one_per_day(tr, tz=TZ)
    out["concentration"] = rb.concentration(tr, TZ)
    out["without_top5_trades"] = rb.stats(tr["r"].sort_values().iloc[:-5]) if len(tr) > 5 else rb.stats([])
    nd = pd.Series([d.date() in NEWS_DAYS for d in pd.to_datetime(tr["day"])])
    out["news_days_diag"] = {"news": rb.stats(tr.loc[nd.values, "r"]), "no_news": rb.stats(tr.loc[~nd.values, "r"])}
    if full:
        out["full_report"] = rb.full_report(tr, TZ)
    # C1
    if pool is not None:
        ctrl = match_control(tr, pool)
        d = tr["r"].to_numpy() - ctrl
        ok = np.isfinite(d)
        tr_ne = simulate_trades(feat, tr[["time", "signal_time", "sym", "dir", "day", "move", "stop"]], H, early=False)
        d2 = tr_ne["r"].to_numpy() - ctrl
        out["C1"] = {"matched": int(ok.sum()), "unmatched": int((~ok).sum()),
                     "e001_mean_matched": float(np.nanmean(tr["r"].to_numpy()[ok])) if ok.any() else np.nan,
                     "control_mean": float(np.nanmean(ctrl)) if ok.any() else np.nan,
                     "diff_mean": float(np.nanmean(d)) if ok.any() else np.nan,
                     "diff_ci95_days": day_boot_mean(d, tr["day"].to_numpy()),
                     "diag_no_early_exit_diff_mean": float(np.nanmean(d2)) if np.isfinite(d2).any() else np.nan,
                     "pool_size": int(len(pool))}
    # C2 jambe inverse
    tri, _ = make_trades(f, thr, start, end, leg="inverse")
    tri = simulate_trades(feat, tri, H, early=True).dropna(subset=["r"])
    out["C2_inverse_leg"] = rb.stats(tri["r"])
    # P1 décalé 60 min
    trp, _ = make_trades(flag, thr, start, end)
    trp = simulate_trades(feat, trp, H, early=True).dropna(subset=["r"])
    out["P1_shift60"] = rb.stats(trp["r"])
    # P2 sens aléatoire
    rev = tr[["time", "signal_time", "sym", "dir", "day", "move", "stop"]].copy()
    rev["dir"] = -rev["dir"]
    rr = simulate_trades(feat, rev, H, early=True)["r"].to_numpy()
    rf = tr["r"].to_numpy()
    rng = np.random.default_rng(7)
    draws = np.array([np.where(rng.random(len(rf)) < 0.5, rf, rr).mean() for _ in range(1000)])
    out["P2_random_dir"] = {"p95": float(np.nanquantile(draws, .95)), "mean": float(np.nanmean(draws)),
                            "e001_exp": float(rf.mean())}
    return out, tr


def train_criteria(v, neigh_exps):
    s = v["stats"]
    c = {}
    c["1_n100_exp005_t2"] = bool(s["n"] >= 100 and s["exp"] > 0.05 and s["t"] >= 2)
    c["2_day_ci_lo_gt0"] = bool(v.get("day_view", {}).get("ci95", [np.nan])[0] > 0)
    c["3_pf_ge_110"] = bool(s["pf"] >= 1.10) if s["n"] else False
    c["4_without_top5_trades_gt0"] = bool(v.get("without_top5_trades", {}).get("exp", np.nan) > 0)
    c["5_one_neighbor_gt0"] = bool(any(e > 0 for e in neigh_exps))
    c1 = v.get("C1", {})
    c["6_C1_diff_ge005_ci_lo_gt0"] = bool(c1.get("diff_mean", np.nan) >= 0.05 and c1.get("diff_ci95_days", [np.nan])[0] > 0)
    c["7_C2_fautive_gt_inverse"] = bool(s["n"] and s["exp"] > v["C2_inverse_leg"]["exp"]) if "C2_inverse_leg" in v else False
    c["8_P1_abs_lt003_and_P2_gt_p95"] = bool(abs(v.get("P1_shift60", {}).get("exp", np.nan)) < 0.03
                                            and v.get("P2_random_dir", {}).get("e001_exp", np.nan) > v.get("P2_random_dir", {}).get("p95", np.nan))
    c["9_costs_06_gt0"] = bool(v.get("costs", {}).get("0.6", {}).get("exp", np.nan) > 0)
    con = v.get("concentration", {})
    c["10_concentration"] = bool(con and con["top5_days_share"] is not None and 0 <= con["top5_days_share"] < 0.40
                                 and con["without_best_quarter"]["exp"] > 0 and con["without_best_pair"]["exp"] > 0)
    return c


def do_train():
    from test_lookahead import run as la_run
    w = WINDOWS["train"]
    raw = load_window("train")
    out = {"window": w, "lookahead_test": la_run(raw, 15)}
    feats = {W: Features(raw, W) for W in (15, 30)}
    frames = {W: feats[W].frame() for W in feats}
    lags = {W: feats[W].frame(lag=60) for W in feats}
    # pools de contrôle : seuil de mouvement minimal = 0,9 × plus petit mouvement des trades E001 de ce W
    pools = {}
    for W in (15, 30):
        mins = {}
        for thr in (2.5, 3.0):
            tr, _ = make_trades(frames[W], thr, w["start"], w["end"])
            for s, g in tr.groupby("sym"):
                mins[s] = min(mins.get(s, np.inf), 0.9 * g["move"].min())
        for H in (20, 30):
            pools[(W, H)] = control_pool(feats[W], frames[W], w["start"], w["end"], H, mins)
    res = {}
    for vid, p in VARIANTS.items():
        res[vid], _ = evaluate(feats[p["W"]], frames[p["W"]], lags[p["W"]], p["thr"], p["H"], w["start"], w["end"],
                               pool=pools[(p["W"], p["H"])])
        res[vid]["params"] = p
    exps = {k: (v["stats"]["exp"] if v["stats"]["n"] else -np.inf) for k, v in res.items()}
    for k in res:
        res[k]["neighbors"] = neighbors(k)
        res[k]["prudent_score"] = min([exps[k]] + [exps[n] for n in neighbors(k)])
    elig = [k for k in res if res[k]["stats"]["n"] >= 100]
    pick_from = elig if elig else list(res)
    sel = max(pick_from, key=lambda k: (res[k]["prudent_score"], -int(k[1:])))
    crit = train_criteria(res[sel], [exps[n] for n in neighbors(sel)])
    out.update({"variants": res, "eligible_n100": elig, "selected": sel, "selection_rule": "max prudent score (min of self+3 neighbors) among n>=100",
                "criteria": crit, "train_pass": all(crit.values()) and out["lookahead_test"]["pass"]})
    RES.mkdir(exist_ok=True)
    (RES / "train.json").write_text(json.dumps(clean(out), indent=1, ensure_ascii=False))
    print(json.dumps(clean({"selected": sel, "stats": res[sel]["stats"], "C1": res[sel].get("C1"), "criteria": crit,
                            "pass": out["train_pass"], "lookahead": out["lookahead_test"]["pass"]}), indent=1))
    for k, v in res.items():
        print(k, clean(v["stats"]), "C1", clean(v.get("C1", {}).get("diff_mean")), "score", clean(v["prudent_score"]))


def do_validation():
    tj = json.loads((RES / "train.json").read_text())
    if not tj.get("train_pass"):
        sys.exit("Critères Train non remplis : validation interdite.")
    sel = tj["selected"]
    p = VARIANTS[sel]
    out = {"variant": sel, "params": p, "windows": {}}
    trades = []
    for name in ("valA", "valB"):
        w = WINDOWS[name]
        raw = load_window(name)
        feat = Features(raw, p["W"])
        f, fl = feat.frame(), feat.frame(lag=60)
        tr0, _ = make_trades(f, p["thr"], w["start"], w["end"])
        mins = {s: 0.9 * g["move"].min() for s, g in tr0.groupby("sym")}
        pool = control_pool(feat, f, w["start"], w["end"], p["H"], mins)
        r, tr = evaluate(feat, f, fl, p["thr"], p["H"], w["start"], w["end"], pool=pool, full=True)
        ctrl = match_control(tr, pool)
        tr["d"] = tr["r"].to_numpy() - ctrl
        out["windows"][name] = r
        trades.append(tr)
    allt = pd.concat(trades, ignore_index=True)
    pooled = {"full_report": rb.full_report(allt, TZ), "C1_diff_mean": float(np.nanmean(allt["d"])),
              "C1_diff_ci95_days": day_boot_mean(allt["d"].to_numpy(), allt["day"].to_numpy())}
    out["pooled"] = pooled
    g = pooled["full_report"]
    c = {"1_exp_gt0_valA_and_valB": all(out["windows"][n]["stats"]["exp"] > 0 for n in ("valA", "valB")),
         "2_pooled_exp_ge003": g["global"]["exp"] >= 0.03,
         "3_costs06_pooled_gt0": g["costs"]["0.6"]["exp"] > 0,
         "4_day_ci_lo_gt0": g["day_view"]["ci95"][0] > 0,
         "5_C1_pooled_gt0": pooled["C1_diff_mean"] > 0,
         "6_top5_days_lt40": g["concentration"]["top5_days_share"] is not None and 0 <= g["concentration"]["top5_days_share"] < 0.40}
    out["criteria"] = c
    out["validation_pass"] = all(bool(v) for v in c.values())
    (RES / "validation.json").write_text(json.dumps(clean(out), indent=1, ensure_ascii=False))
    print(json.dumps(clean({"criteria": c, "pass": out["validation_pass"], "global": g["global"],
                            "A": out["windows"]["valA"]["stats"], "B": out["windows"]["valB"]["stats"]}), indent=1))


if __name__ == "__main__":
    {"train": do_train, "validation": do_validation}[sys.argv[1]]()
