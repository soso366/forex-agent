"""E002 — exécution : python3 experiments/E002-…/code/run.py count|train|validation

count      : nombre de signaux par paire et par variante (AUCUN R calculé) → stdout (recopié dans protocol.md)
train      : 8 variantes + contrôles (spread normal, minutes rondes, artefact A1/A2) + placebo + coûts + vue par jour
             + épisodes + concentration + contrôle données + fériés + test de non-look-ahead → results/train.json
validation : variante retenue uniquement, si et seulement si train.json "passed" = true → results/validation.json
L'OOS vierge n'est PAS implémenté ici (lecture unique ultérieure, après oos-gate).
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
from e002 import (FALLBACK, HOLIDAYS, N_MIN_PRINCIPAL, PAIRS, PRINCIPAL, TZ, VARIANTS, WINDOWS,  # noqa: E402
                  PairFeatures, day_boot_diff, episodes, load_window, neighbors, placebo, run_trades, signals)
from research.common import robustness as rb  # noqa: E402

RES = HERE.parent / "results"
COSTS = (0.0, 0.2, 0.4, 0.5, 0.6, 1.0)


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) else ("inf" if math.isinf(f) else round(f, 5))
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o)
    return o


def count(feats, w):
    out = {}
    for thr in (3.0, 2.5):
        t = signals(feats, thr, w["start"], w["end"])
        out[str(thr)] = {"n": int(len(t)), "per_pair": t["sym"].value_counts().to_dict() if len(t) else {},
                         "isolated": int(t["isolated"].sum()) if len(t) else 0}
    return out


def describe(t: pd.DataFrame) -> dict:
    s = rb.stats(t["r"])
    out = {"stats": s}
    if len(t) == 0:
        return out
    out["exits"] = t["exit"].value_counts().to_dict()
    out["pairs"] = {k: rb.stats(g["r"]) for k, g in t.groupby("sym")}
    out["costs"] = rb.costs(t, COSTS)
    out["day_view"] = rb.day_view(t, TZ)
    out["one_per_day"] = rb.one_per_day(t, tz=TZ)
    ep = episodes(t)
    em = t.assign(_e=ep).groupby("_e")["r"].mean()
    out["episode_view"] = rb.stats(em)
    tot = t["r"].sum()
    out["max_episode_share"] = float(t.assign(_e=ep).groupby("_e")["r"].sum().max() / tot) if tot > 0 else None
    out["concentration"] = rb.concentration(t, TZ)
    out["without_top5_trades"] = rb.stats(t["r"].sort_values().iloc[:-5]) if len(t) > 5 else rb.stats([])
    top = t.sort_values("r", ascending=False).head(10)
    out["top10_trades"] = [{"time": str(r.time), "sym": r.sym, "r": r.r, "dir": r.dir, "move_atr": r.move_atr,
                            "spread_x": r.spread_x, "exit": r.exit} for r in top.itertuples()]
    iso = t["isolated"].astype(bool).to_numpy()
    out["data_control_isolated"] = {"n_isolated": int(iso.sum()), "share_trades": float(iso.mean()),
                                    "share_R": float(t.loc[iso, "r"].sum() / tot) if tot else None,
                                    "without_isolated": rb.stats(t.loc[~iso, "r"])}
    hol = np.array([d in HOLIDAYS for d in t["day"]])
    mon = pd.DatetimeIndex(t["time"]).weekday.to_numpy() == 0
    out["holidays"] = {"n_holiday": int(hol.sum()), "with": s, "without": rb.stats(t.loc[~hol, "r"]),
                       "monday": rb.stats(t.loc[mon, "r"]), "not_monday": rb.stats(t.loc[~mon, "r"])}
    return out


def evaluate(feats, p, w, do_placebo=True):
    tr = run_trades(feats, signals(feats, p["thr"], w["start"], w["end"]), p["H"], p["tgt"])
    out = describe(tr)
    # Contrôle 1 : même mouvement, spread normal (< 1,5 × ref), même code
    cn = run_trades(feats, signals(feats, p["thr"], w["start"], w["end"], spread="normal"), p["H"], p["tgt"])
    out["C_spread_normal"] = {"stats": rb.stats(cn["r"]),
                              "diff": (out["stats"]["exp"] - rb.stats(cn["r"])["exp"]) if len(tr) and len(cn) else np.nan,
                              "diff_ci95_days": day_boot_diff(tr, cn)}
    # Contrôle 2 : minutes rondes
    cr = run_trades(feats, signals(feats, p["thr"], w["start"], w["end"], rnd=True), p["H"], p["tgt"])
    out["C_round_minutes"] = {"stats": rb.stats(cr["r"]),
                              "diff_offround_minus_round": (out["stats"]["exp"] - rb.stats(cr["r"])["exp"])
                              if len(tr) and len(cr) else np.nan}
    # Contrôle 3 : artefact de cotation (Δ sur le côté exécutable)
    for k in ("A1", "A2"):
        ca = run_trades(feats, signals(feats, p["thr"], w["start"], w["end"], dmode=k), p["H"], p["tgt"])
        out[f"C_artefact_{k}"] = {"stats": rb.stats(ca["r"])}
    if do_placebo and len(tr):
        pl = placebo(feats, tr, p["H"], p["tgt"])
        pl["e002_exp"] = out["stats"]["exp"]
        out["placebo_time"] = pl
    return out, tr


def train_criteria(v, neigh_exps, principal):
    s = v["stats"]
    n = s["n"]
    g = lambda d, *ks: _get(d, ks)  # noqa: E731
    c = {}
    c["1_n80_exp005_t2"] = bool(n >= 80 and s["exp"] > 0.05 and s["t"] >= 2)
    c["2_principal_exp_gt0_t2"] = bool(principal["stats"]["n"] and principal["stats"]["exp"] > 0 and principal["stats"]["t"] >= 2)
    c["3_pf_ge_110"] = bool(n and s["pf"] >= 1.10)
    c["4_without_top5_trades_gt0"] = bool(g(v, "without_top5_trades", "exp") > 0)
    c["5_one_neighbor_gt0"] = bool(any(e > 0 for e in neigh_exps))
    c["6_day_ci_lo_gt0"] = bool(g(v, "day_view", "ci95", 0) > 0)
    c["7_C_spread_normal_diff_ge008_ci_lo_gt0"] = bool(g(v, "C_spread_normal", "diff") >= 0.08
                                                       and g(v, "C_spread_normal", "diff_ci95_days", 0) > 0)
    nr = g(v, "C_round_minutes", "stats", "n")
    c["8_C_round_minutes_diff_ge005_if_n50"] = bool(g(v, "C_round_minutes", "diff_offround_minus_round") >= 0.05) \
        if (nr is not None and nr >= 50) else True
    c["9_C_artefact_A1_gt0_A2_n30_gt0"] = bool(g(v, "C_artefact_A1", "stats", "exp") > 0
                                               and (g(v, "C_artefact_A2", "stats", "n") or 0) >= 30
                                               and g(v, "C_artefact_A2", "stats", "exp") > 0)
    c["10_placebo_gt_p95"] = bool(g(v, "placebo_time", "e002_exp") > g(v, "placebo_time", "p95"))
    c["11_costs_05_and_06_gt0"] = bool(g(v, "costs", "0.5", "exp") > 0 and g(v, "costs", "0.6", "exp") > 0)
    sh = g(v, "concentration", "top5_days_share")
    me = v.get("max_episode_share")
    c["12_concentration"] = bool(sh is not None and 0 <= sh < 0.40 and me is not None and me < 0.40
                                 and g(v, "concentration", "without_best_quarter", "exp") > 0
                                 and g(v, "concentration", "without_best_pair", "exp") > 0)
    c["13_without_isolated_gt0"] = bool(g(v, "data_control_isolated", "without_isolated", "exp") > 0)
    c["14_without_holidays_gt0"] = bool(g(v, "holidays", "without", "exp") > 0)
    return c


def _get(d, ks):
    for k in ks:
        try:
            d = d[k]
        except (KeyError, IndexError, TypeError):
            return np.nan
    return np.nan if d is None else d


def do_count():
    w = WINDOWS["train"]
    raw = load_window("train")
    feats = {s: PairFeatures(raw[s]) for s in PAIRS}
    print(json.dumps(clean(count(feats, w)), indent=1))


def do_train():
    from test_lookahead import run as la_run
    w = WINDOWS["train"]
    raw = load_window("train")
    feats = {s: PairFeatures(raw[s]) for s in PAIRS}
    out = {"experiment": "E002", "window": w, "lookahead_test": la_run(raw)}
    cnt = count(feats, w)
    out["signal_counts"] = cnt
    principal = PRINCIPAL if cnt["3.0"]["n"] >= N_MIN_PRINCIPAL else FALLBACK
    out["principal_rule"] = {"id": principal, "rule": f"{PRINCIPAL} si n(3x) >= {N_MIN_PRINCIPAL}, sinon {FALLBACK}"}
    res = {}
    for vid, p in VARIANTS.items():
        res[vid], _ = evaluate(feats, p, w)
        res[vid]["params"] = p
    exps = {k: (v["stats"]["exp"] if v["stats"]["n"] else -np.inf) for k, v in res.items()}
    for k in res:
        res[k]["neighbors"] = neighbors(k)
        res[k]["prudent_score"] = min([exps[k]] + [exps[n] for n in neighbors(k)])
    elig = [k for k in res if res[k]["stats"]["n"] >= 80]
    pick = elig if elig else list(res)
    sel = max(pick, key=lambda k: (res[k]["prudent_score"], -int(k[1:])))
    crit = train_criteria(res[sel], [exps[n] for n in neighbors(sel)], res[principal])
    crit["15_lookahead_test_pass"] = bool(out["lookahead_test"]["pass"])
    out.update({"variants": res, "eligible_n80": elig, "selected": sel,
                "selection_rule": "max score prudent (min de soi + 3 voisins) parmi n >= 80 ; aucune éligible → "
                                  "meilleur score prudent rapporté, critère 1 échoue",
                "criteria": crit, "passed": all(crit.values())})
    out["mechanism_round_minutes"] = ("décisif" if (res[sel]["C_round_minutes"]["stats"]["n"] >= 50)
                                      else "n < 50 : non décisif, mécanisme NON confirmé")
    RES.mkdir(exist_ok=True)
    (RES / "train.json").write_text(json.dumps(clean(out), indent=1, ensure_ascii=False))
    print(json.dumps(clean({"selected": sel, "principal": principal, "stats": res[sel]["stats"],
                            "C_spread_normal": res[sel]["C_spread_normal"], "criteria": crit,
                            "passed": out["passed"]}), indent=1))
    for k, v in res.items():
        print(k, clean(v["stats"]), "ctrl_normal", clean(v["C_spread_normal"]["stats"]["exp"]),
              "score", clean(v["prudent_score"]))


def do_validation():
    tj = json.loads((RES / "train.json").read_text())
    if not tj.get("passed"):
        sys.exit("Critères Train non remplis : validation interdite.")
    sel = tj["selected"]
    p = VARIANTS[sel]
    out = {"variant": sel, "params": p, "windows": {}}
    trs, ctrls = [], []
    for name in ("valA", "valB"):
        w = WINDOWS[name]
        raw = load_window(name)
        feats = {s: PairFeatures(raw[s]) for s in PAIRS}
        r, tr = evaluate(feats, p, w, do_placebo=False)
        r["full_report"] = rb.full_report(tr, TZ) if len(tr) else {}
        out["windows"][name] = r
        trs.append(tr)
        ctrls.append(run_trades(feats, signals(feats, p["thr"], w["start"], w["end"], spread="normal"), p["H"], p["tgt"]))
    allt, allc = pd.concat(trs, ignore_index=True), pd.concat(ctrls, ignore_index=True)
    g = rb.full_report(allt, TZ)
    pooled = {"full_report": g, "C_spread_normal_diff": rb.stats(allt["r"])["exp"] - rb.stats(allc["r"])["exp"],
              "C_spread_normal_diff_ci95_days": day_boot_diff(allt, allc)}
    out["pooled"] = pooled
    c = {"1_exp_gt0_valA_and_valB": all(out["windows"][n]["stats"]["exp"] > 0 for n in ("valA", "valB")),
         "2_pooled_exp_ge003": g["global"]["exp"] >= 0.03,
         "3_costs06_pooled_gt0": g["costs"]["0.6"]["exp"] > 0,
         "4_day_ci_lo_gt0": g["day_view"]["ci95"][0] > 0,
         "5_C_spread_normal_pooled_diff_gt0": pooled["C_spread_normal_diff"] > 0,
         "6_top5_days_lt40": g["concentration"]["top5_days_share"] is not None
         and 0 <= g["concentration"]["top5_days_share"] < 0.40}
    out["criteria"] = c
    out["passed"] = all(bool(v) for v in c.values())
    (RES / "validation.json").write_text(json.dumps(clean(out), indent=1, ensure_ascii=False))
    print(json.dumps(clean({"criteria": c, "passed": out["passed"], "global": g["global"]}), indent=1))


if __name__ == "__main__":
    {"count": do_count, "train": do_train, "validation": do_validation}[sys.argv[1]]()
