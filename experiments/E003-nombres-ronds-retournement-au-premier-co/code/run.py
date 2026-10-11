"""E003 — exécution : python3 experiments/E003-…/code/run.py count|train|validation|oos

count      : nombre de signaux (A–F, voisins, placebos) par paire et par mois, AUCUN R calculé
             → results/signal_counts.json (à COMMITER avant `train`, exigence 2 du Critic)
train      : refuse de tourner si signal_counts.json n'est pas commité ; A + placebos (28 grilles) + B–F + voisins
             + coûts + stress + vue par jour + règles live + concentration + diagnostics → results/train.json
             Train échoué → validation.json et oos.json = {"skipped": "Train échoué"}.
validation : A uniquement, si train.json "passed" = true → results/validation.json
oos        : A uniquement, si `python -m orchestrator oos-gate E003` = OUVERT → results/oos.json (lecture unique)
"""
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
from e003 import (N_MIN, PAIRS, PLACEBO_NAMED, PLACEBO_OFFSETS, ROOT, SENSITIVITY, TZ, VARIANTS,  # noqa: E402
                  WINDOWS, PairData, candidates, day_boot_diff, day_t, live_rules, load_window, percentile_rank,
                  rb, signals, simulate_trades)

EXP_DIR = HERE.parent
RES = EXP_DIR / "results"
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
    if isinstance(o, (pd.Timestamp,)):
        return str(o)
    return o


def write(name, obj):
    RES.mkdir(exist_ok=True)
    (RES / name).write_text(json.dumps(clean(obj), indent=1, ensure_ascii=False))


def prep(name):
    raw = load_window(name)
    return {s: PairData(raw[s], s) for s in PAIRS}, WINDOWS[name]


def sig_variant(pdata, w, vid, offset=0):
    v = VARIANTS[vid]
    return signals(pdata, w, spacing=v["spacing"], offset=offset, H=v["H"], stop=v["stop"], tgt=v["tgt"])


def sig_sens(pdata, w, sid, offset=0):
    return signals(pdata, w, offset=offset, **SENSITIVITY[sid])


def count_table(sig):
    if sig.empty:
        return {"n": 0, "per_pair": {}, "per_month": {}}
    mo = pd.DatetimeIndex(sig["time"]).strftime("%Y-%m")
    return {"n": int(len(sig)), "per_pair": sig["sym"].value_counts().to_dict(),
            "per_month": pd.Series(mo).value_counts().sort_index().to_dict(),
            "per_pair_month": sig.assign(_m=mo).groupby(["sym", "_m"]).size().unstack(fill_value=0).to_dict("index"),
            "level00": int(sig["level00"].sum()), "level50": int((~sig["level00"].astype(bool)).sum()),
            "spread_contacts": int(sig["spread_contact"].sum())}


# ------------------------------------------------------------------ count (aucun R)
def do_count():
    pdata, w = prep("train")
    out = {"experiment": "E003", "window": {k: w[k] for k in ("start", "end")},
           "note": "comptage AVANT tout calcul de R (aucun appel à simulate)", "variants": {}, "sensitivity": {},
           "placebo": {}}
    for vid in VARIANTS:
        out["variants"][vid] = count_table(sig_variant(pdata, w, vid))
    for sid in SENSITIVITY:
        out["sensitivity"][sid] = count_table(sig_sens(pdata, w, sid))
    for o in PLACEBO_OFFSETS:
        out["placebo"][f"+{o}"] = count_table(sig_variant(pdata, w, "A", offset=o))
    out["A_eligible_n80"] = out["variants"]["A"]["n"] >= N_MIN
    write("signal_counts.json", out)
    print(json.dumps(clean({"A": out["variants"]["A"], "B": out["variants"]["B"]["n"],
                            "placebo+17": out["placebo"]["+17"]["n"], "placebo+33": out["placebo"]["+33"]["n"]}),
                     indent=1))


def counts_committed() -> bool:
    p = RES / "signal_counts.json"
    if not p.exists():
        return False
    rel = str(p.relative_to(ROOT))
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=ROOT, capture_output=True).returncode == 0
    clean_ = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT).returncode == 0
    return tracked and clean_


# ------------------------------------------------------------------ description d'un ensemble de trades
def describe(t: pd.DataFrame, full=True) -> dict:
    s = rb.stats(t["r"]) if len(t) else rb.stats([])
    out = {"stats": s}
    if len(t) == 0:
        return out
    out["day_t"] = day_t(t)
    out["costs"] = rb.costs(t, COSTS)
    out["stress_worst_price"] = {
        "stats": rb.stats(t["r_stress"]),
        "stop_mean_r": float(t.loc[t["exit"] == "stop", "r_stress"].mean()) if (t["exit"] == "stop").any() else None,
        "share_losses_below_m1.2R": float((t["r_stress"] < -1.2).mean()),
        "costs_0.5pip": rb.stats(t["r_stress"] - 0.5 * t["sym"].map(rb.PIP) / t["stop"])}
    if not full:
        return out
    m = pd.DatetimeIndex(t["time"]).month
    half1 = np.isin(m, [9, 10, 11])
    months = t.groupby(pd.DatetimeIndex(t["time"]).strftime("%Y-%m"))["r"].sum()
    tot = t["r"].sum()
    pairs_R = t.groupby("sym")["r"].sum()
    out.update({
        "exits": t["exit"].value_counts().to_dict(),
        "minutes_max": float(t["minutes"].max()),
        "pairs": {k: rb.stats(g["r"]) for k, g in t.groupby("sym")},
        "best_pair_share": float(pairs_R.max() / tot) if tot > 0 else None,
        "day_view": rb.day_view(t, TZ),
        "one_per_day": rb.one_per_day(t, tz=TZ),
        "concentration": rb.concentration(t, TZ),
        "quarters": rb.quarters(t),
        "halves": {"sept-nov": rb.stats(t.loc[half1, "r"]), "dec-fev": rb.stats(t.loc[~half1, "r"])},
        "months_R": months.to_dict(), "months_positive": int((months > 0).sum()), "months_total": int(len(months)),
        "level00": rb.stats(t.loc[t["level00"].astype(bool), "r"]),
        "level50": rb.stats(t.loc[~t["level00"].astype(bool), "r"]),
        "spread_contacts": {"n": int(t["spread_contact"].sum()), "share": float(t["spread_contact"].mean()),
                            "without": rb.stats(t.loc[~t["spread_contact"].astype(bool), "r"])},
        "atr_pips": {k: float(v) for k, v in t["atr_pips"].describe(percentiles=[.1, .25, .5, .75, .9]).items()},
        "atr_terciles": {str(k): rb.stats(g["r"]) for k, g in
                         t.groupby(pd.qcut(t["atr_pips"], 3, labels=["bas", "moyen", "haut"]), observed=True)},
        "hours_utc": {str(k): rb.stats(g["r"]) for k, g in t.groupby(pd.DatetimeIndex(t["contact_time"]).hour)},
        "sessions": {k: rb.stats(g["r"]) for k, g in t.groupby(np.select(
            [pd.DatetimeIndex(t["contact_time"]).hour < 12, pd.DatetimeIndex(t["contact_time"]).hour < 16],
            ["londres 07-12", "overlap 12-16"], "new_york 16-19:30"))},
        "directions": {("achat" if k > 0 else "vente"): rb.stats(g["r"]) for k, g in t.groupby("dir")},
        "top10_trades": [{"time": str(r.time), "sym": r.sym, "dir": int(r.dir), "L": r.L, "r": r.r, "exit": r.exit}
                         for r in t.sort_values("r", ascending=False).head(10).itertuples()],
    })
    lv = live_rules(t)
    out["live_rules"] = {"stats": rb.stats(lv["r"]), "day_t": day_t(lv)}
    out["journal_audit"] = journal(t)
    return out


def journal(t: pd.DataFrame) -> dict:
    """Meta-skill journal_audit sur les trades simulés (informatif)."""
    try:
        from forex_agent.meta import journal_audit as ja
        j = pd.DataFrame({"entry_time": t["time"].astype(str), "exit_time": t["exit_time"].astype(str),
                          "r_multiple": t["r"], "exit_reason": t["exit"], "symbol": t["sym"], "strategy": "E003",
                          "duration_min": t["minutes"], "mfe_r": t["mfe_r"], "mae_r": t["mae_r"]})
        res = ja.audit(j)
        return {k: res[k] for k in ("global", "by_weekday", "hidden_correlations", "losing_streaks", "observations")}
    except Exception as e:  # informatif : ne bloque jamais la mesure
        return {"error": repr(e)}


def placebo_block(pdata, w, tA, sig_fn=None) -> dict:
    """28 grilles décalées (même code, seul le décalage change) + IC jour sur ronde − moyenne des placebos."""
    sets, exps = [tA], {}
    for o in PLACEBO_OFFSETS:
        tp = simulate_trades(pdata, sig_variant(pdata, w, "A", offset=o))
        sets.append(tp)
        exps[f"+{o}"] = rb.stats(tp["r"]) if len(tp) else rb.stats([])
    eA = rb.stats(tA["r"])["exp"] if len(tA) else np.nan
    dist = [exps[k]["exp"] for k in exps]
    return {"round_exp": eA, "grids": exps,
            "named": {f"+{o}": {"exp": exps[f"+{o}"]["exp"], "n": exps[f"+{o}"]["n"],
                                "diff": eA - exps[f"+{o}"]["exp"]} for o in PLACEBO_NAMED},
            "percentile_rank": percentile_rank(eA, dist), "n_grids": len(dist),
            "placebo_mean_exp": float(np.nanmean(dist)), "placebo_q90": float(np.nanquantile(dist, .9)),
            "diff_round_minus_mean_ci95_days": day_boot_diff(sets)}


def cascade_diag(pdata, w) -> dict:
    out = {}
    for o in (0,) + PLACEBO_NAMED:
        parts = [candidates(pdata[s], offset=o, start=w["start"], end=w["end"], cascade=True) for s in PAIRS]
        c = pd.concat([x for x in parts if len(x)] or [pd.DataFrame(columns=["move5_atr"])], ignore_index=True)
        mv = pd.Series(c.get("move5_atr", []), dtype=float).dropna()
        out[f"+{o}"] = {"n": int(len(mv)), "mean_move5_atr": float(mv.mean()) if len(mv) else None,
                        "t": float(mv.mean() / (mv.std(ddof=1) / np.sqrt(len(mv)))) if len(mv) > 2 else None}
    out["note"] = "diagnostic uniquement (prédiction 2 d'Osler) ; interdit d'en faire une règle de continuation"
    return out


def gradient(tA) -> dict:
    a, b = tA[tA["level00"].astype(bool)], tA[~tA["level00"].astype(bool)]
    n00, n50 = len(a), len(b)
    e00 = rb.stats(a["r"])["exp"] if n00 else np.nan
    e50 = rb.stats(b["r"])["exp"] if n50 else np.nan
    concl = n00 >= 40 and n50 >= 40
    return {"n00": n00, "n50": n50, "exp00": e00, "exp50": e50, "conclusive": concl,
            "ok": bool(e00 >= e50 - 0.10) if concl else None}


def lookahead_real(pdata) -> dict:
    from test_synthetic import lookahead_checks
    res, ok = {}, True
    for s, f in pdata.items():
        days = sorted({d for d in pd.DatetimeIndex(f.df.index).normalize() if d.weekday() < 5})
        t0 = days[min(20, len(days) - 1)] + pd.Timedelta(hours=10, minutes=7)
        r = lookahead_checks(f.df, s, t0)
        res[s] = r
        ok &= r["pass"]
    res["pass"] = bool(ok)
    return res


# ------------------------------------------------------------------ train
def do_train():
    if not counts_committed():
        sys.exit("results/signal_counts.json absent ou non commité : lancer `run.py count`, COMMITER, puis `train` "
                 "(exigence 2 du Critic : comptage avant tout R).")
    pdata, w = prep("train")
    from test_synthetic import run_all
    out = {"experiment": "E003", "window": {k: w[k] for k in ("start", "end")},
           "synthetic_test": run_all(), "lookahead_real": lookahead_real(pdata)}
    tA = simulate_trades(pdata, sig_variant(pdata, w, "A"))
    A = describe(tA)
    A["placebo"] = placebo_block(pdata, w, tA)
    A["gradient_00_50"] = gradient(tA)
    out["A"] = A
    out["variants_diag"] = {}
    for vid in [v for v in VARIANTS if v != "A"]:
        tv = simulate_trades(pdata, sig_variant(pdata, w, vid))
        d = describe(tv, full=False)
        if vid == "B":    # B comparé à ses deux placebos nommés (grille de 100 pips décalée)
            d["placebo_named"] = {f"+{o}": rb.stats(simulate_trades(pdata, sig_variant(pdata, w, vid, o))["r"])
                                  for o in PLACEBO_NAMED}
        out["variants_diag"][vid] = d
    out["sensitivity"] = {sid: describe(simulate_trades(pdata, sig_sens(pdata, w, sid)), full=False)
                          for sid in SENSITIVITY}
    out["cascade_diag"] = cascade_diag(pdata, w)
    out["criteria"] = train_criteria(out)
    out["passed"] = all(v is True for v in out["criteria"].values())
    write("train.json", out)
    if not out["passed"]:
        write("validation.json", {"skipped": "Train échoué"})
        write("oos.json", {"skipped": "Train échoué"})
    print(json.dumps(clean({"A": A["stats"], "day_t": A.get("day_t"), "criteria": out["criteria"],
                            "passed": out["passed"]}), indent=1))


def g(d, *ks):
    for k in ks:
        try:
            d = d[k]
        except (KeyError, IndexError, TypeError):
            return np.nan
    return np.nan if d is None else d


def train_criteria(o) -> dict:
    A = o["A"]
    s = A["stats"]
    pl = A["placebo"]
    c = {}
    c["T1_n_ge_80"] = bool(s["n"] >= N_MIN)
    c["T2_exp_gt_0.05"] = bool(s["n"] and s["exp"] > 0.05)
    c["T3_day_t_ge_2"] = bool(g(A, "day_t", "t") >= 2)
    c["T4_beats_+17_and_+33_by_0.06"] = bool(all(g(pl, "named", k, "diff") >= 0.06 for k in ("+17", "+33")))
    c["T5_percentile_ge_90"] = bool(g(pl, "percentile_rank") >= 90)
    c["T6_day_ci95_diff_lo_gt_0"] = bool(g(pl, "diff_round_minus_mean_ci95_days", "ci95", 0) > 0)
    gr = A["gradient_00_50"]
    c["T7_gradient_00_50"] = True if gr["ok"] is None else bool(gr["ok"])   # non concluant ≠ échec au Train
    c["T8_costs_0.5pip_gt_0"] = bool(g(A, "costs", "0.5", "exp") > 0)
    c["T9_stress_worst_price_gt_0"] = bool(g(A, "stress_worst_price", "stats", "exp") > 0)
    sh = g(A, "concentration", "top5_days_share")
    bp = g(A, "best_pair_share")
    c["T10a_top5_days_le_40pct"] = bool(s["R"] > 0 and 0 <= sh <= 0.40)
    c["T10b_best_pair_le_70pct"] = bool(s["R"] > 0 and bp <= 0.70)
    c["T10c_both_halves_positive"] = bool(g(A, "halves", "sept-nov", "R") > 0 and g(A, "halves", "dec-fev", "R") > 0)
    c["T10d_months_positive_ge_4"] = bool(g(A, "months_positive") >= 4)
    c["T11_spread_contacts_le_20pct_and_without_gt_0"] = bool(g(A, "spread_contacts", "share") <= 0.20
                                                              and g(A, "spread_contacts", "without", "exp") > 0)
    c["T12_live_rules_exp_gt_0"] = bool(g(A, "live_rules", "stats", "exp") > 0)
    c["T13_neighbors_same_sign"] = bool(all(g(o, "sensitivity", k, "stats", "exp") > 0 for k in SENSITIVITY))
    c["T14_minutes_le_30"] = bool(g(A, "minutes_max") <= 30)
    c["T15_no_lookahead"] = bool(o["synthetic_test"]["pass"] and o["lookahead_real"]["pass"])
    return c


# ------------------------------------------------------------------ validation
def do_validation():
    tj = json.loads((RES / "train.json").read_text())
    if not tj.get("passed"):
        sys.exit("Critères Train non remplis : validation interdite.")
    pdata, w = prep("validation")
    tA = simulate_trades(pdata, sig_variant(pdata, w, "A"))
    A = describe(tA)
    A["placebo"] = placebo_block(pdata, w, tA)
    A["gradient_00_50"] = gr = gradient(tA)
    if not gr["conclusive"]:     # repli pré-déclaré : Train + Validation groupés
        tT = simulate_trades(pdata, sig_variant(pdata, WINDOWS["train"], "A"))
        A["gradient_00_50_pooled_train_val"] = gr = gradient(pd.concat([tT, tA], ignore_index=True))
    A["full_report"] = rb.full_report(tA, TZ) if len(tA) else {}
    s, pl = A["stats"], A["placebo"]
    c = {"V1_exp_ge_0.03": bool(s["n"] and s["exp"] >= 0.03),
         "V2_beats_+17_and_+33": bool(all(g(pl, "named", k, "diff") > 0 for k in ("+17", "+33"))),
         "V3_percentile_ge_90": bool(g(pl, "percentile_rank") >= 90),
         "V4_diff_round_minus_mean_gt_0": bool(g(pl, "diff_round_minus_mean_ci95_days", "diff") > 0),
         "V5_costs_0.5pip_gt_0": bool(g(A, "costs", "0.5", "exp") > 0),
         "V6_stress_worst_price_gt_0": bool(g(A, "stress_worst_price", "stats", "exp") > 0),
         "V7_day_mean_gt_0": bool(g(A, "day_t", "mean") > 0),
         "V8_gradient_00_50": bool(gr["ok"]) if gr["conclusive"] else False,
         "V9_top5_days_le_40pct": bool(s["R"] > 0 and 0 <= g(A, "concentration", "top5_days_share") <= 0.40),
         "V10_best_pair_le_70pct": bool(s["R"] > 0 and g(A, "best_pair_share") <= 0.70)}
    out = {"experiment": "E003", "window": {k: w[k] for k in ("start", "end")}, "A": A, "criteria": c,
           "passed": all(c.values())}
    write("validation.json", out)
    if not out["passed"]:
        write("oos.json", {"skipped": "Validation échouée"})
    print(json.dumps(clean({"A": s, "criteria": c, "passed": out["passed"]}), indent=1))


# ------------------------------------------------------------------ OOS (lecture unique)
def do_oos():
    gate = subprocess.run([sys.executable, "-m", "orchestrator", "oos-gate", "E003"], cwd=ROOT,
                          capture_output=True, text=True)
    if gate.returncode != 0:
        sys.exit("oos-gate FERMÉ pour E003 : lecture de l'OOS vierge interdite.")
    if (RES / "oos.json").exists():
        sys.exit("results/oos.json existe déjà : l'OOS se lit UNE seule fois.")
    pdata, w = prep("oos")
    tA = simulate_trades(pdata, sig_variant(pdata, w, "A"))
    A = describe(tA)
    A["placebo"] = placebo_block(pdata, w, tA)
    A["full_report"] = rb.full_report(tA, TZ) if len(tA) else {}
    s, pl = A["stats"], A["placebo"]
    e = s["exp"] if s["n"] else np.nan
    c05 = g(A, "costs", "0.5", "exp")
    if not (e > 0) or not (c05 > 0) or g(pl, "percentile_rank") < 50:
        verdict = "FAIL"
    elif (s["n"] >= 60 and e > 0.03 and g(A, "stress_worst_price", "stats", "exp") > 0 and g(A, "day_t", "mean") > 0
          and g(pl, "percentile_rank") >= 90 and all(g(pl, "named", k, "diff") > 0 for k in ("+17", "+33"))):
        verdict = "PASS"
    else:
        verdict = "INCONCLUSIVE"
    write("oos.json", {"experiment": "E003", "window": {k: w[k] for k in ("start", "end")}, "A": A,
                       "verdict": verdict})
    print(json.dumps(clean({"A": s, "verdict": verdict}), indent=1))


if __name__ == "__main__":
    cmds = {"count": do_count, "train": do_train, "validation": do_validation, "oos": do_oos}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]]()
