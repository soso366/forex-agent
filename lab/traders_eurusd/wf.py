"""Backtests du protocole : paramètres par défaut + walk-forward 4 trimestres.

Usage : python wf.py <fichiers EURUSD*.csv.gz ...> [--out DOSSIER]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "oss_eurusd"))
from engine import Costs, Sim, load_m1, metrics, resample  # noqa: E402
from hypotheses import HYPOTHESES, daily_bars  # noqa: E402

TS = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731
FORBIDDEN = (TS("2023-09-01"), TS("2024-09-01"))
DEFAULT_PERIODS = {"entrainement": (TS("2024-09-01"), TS("2025-09-01")),
                   "validation": (TS("2025-09-01"), TS("2026-09-01"))}
FOLDS = [(TS("2024-09-01"), TS("2025-09-01"), TS("2025-12-01")),
         (TS("2024-12-01"), TS("2025-12-01"), TS("2026-03-01")),
         (TS("2025-03-01"), TS("2026-03-01"), TS("2026-06-01")),
         (TS("2025-06-01"), TS("2026-06-01"), TS("2026-09-01"))]
COSTS = {"base": Costs("base", 7.0, 0.2), "stress": Costs("stress", 9.0, 0.5)}


def bars_of(prep):
    return prep[0] if isinstance(prep, tuple) else prep


def run(m1, prep, fn, params, a, b, costs, balance=10_000.0):
    bars = bars_of(prep)
    i0, i1 = int(bars["time"].searchsorted(a)), int(bars["time"].searchsorted(b))
    sim = Sim(m1, costs, balance, i_end=int(m1["time"].searchsorted(b)))
    fn(sim, prep, i0, i1, params)
    sim.close_end()
    return sim


def tstat(pnl):
    pnl = np.asarray(pnl, float)
    if len(pnl) < 3 or pnl.std(ddof=1) == 0:
        return None
    return float(pnl.mean() / (pnl.std(ddof=1) / math.sqrt(len(pnl))))


def pf(pnl):
    pnl = np.asarray(pnl, float)
    gl = -pnl[pnl < 0].sum()
    return float(pnl[pnl > 0].sum() / gl) if gl > 0 else None


def walk_forward(m1, prep, fn, grid, costs):
    balance, eq, trades, folds = 10_000.0, [], [], []
    for is_a, oos_a, oos_b in FOLDS:
        best, best_pf = None, -1.0
        for p in grid:
            s = run(m1, prep, fn, p, is_a, oos_a, costs)
            pnl = [x["pnl"] for x in s.trades]
            v = pf(pnl) if len(pnl) >= 30 else None
            if v is not None and v > best_pf:
                best, best_pf = p, v
        if best is None:
            folds.append({"oos": f"{oos_a.date()}→{oos_b.date()}", "params": None, "trades": 0, "net": 0.0})
            continue
        s = run(m1, prep, fn, best, oos_a, oos_b, costs, balance)
        net = s.balance - balance
        balance = s.balance
        eq += s.equity
        trades += s.trades
        folds.append({"oos": f"{oos_a.date()}→{oos_b.date()}", "params": best, "is_pf": round(best_pf, 3),
                      "trades": len(s.trades), "net": round(net, 2), "pf": pf([x["pnl"] for x in s.trades])})
    pnl = [x["pnl"] for x in trades]
    e = np.array(eq + [balance])
    dd = float(np.max((np.maximum.accumulate(e) - e) / np.maximum.accumulate(e))) * 100 if len(e) else 0.0
    return {"folds": folds, "trades": len(pnl), "pf": round(pf(pnl), 3) if pf(pnl) else None,
            "rentabilite_pct": round((balance / 10_000 - 1) * 100, 2), "drawdown_max_pct": round(dd, 2),
            "t_stat": round(tstat(pnl), 2) if tstat(pnl) is not None else None,
            "trimestres_positifs": sum(1 for f in folds if f["net"] > 0)}, trades


def verdict(res):
    wf, wfs = res["walk_forward"]["base"], res["walk_forward"]["stress"]
    d = res["defaut"]
    checks = {
        "wf_pf_1_20": (wf["pf"] or 0) >= 1.20,
        "wf_60_trades": wf["trades"] >= 60,
        "wf_3_trimestres_sur_4": wf["trimestres_positifs"] >= 3,
        "wf_dd_15": wf["drawdown_max_pct"] <= 15,
        "wf_t_stat_2": (wf["t_stat"] or 0) >= 2.0,
        "defaut_entrainement_positif": d["entrainement_base"]["rentabilite_pct"] > 0,
        "defaut_validation_positif": d["validation_base"]["rentabilite_pct"] > 0,
        "wf_stress_positif": wfs["rentabilite_pct"] > 0,
    }
    checks = {k: bool(v) for k, v in checks.items()}
    return {"criteres": checks, "decision": "PASSE" if all(checks.values()) else "REJETÉE"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default="results/traders_eurusd")
    args = ap.parse_args(argv)
    m1 = load_m1(args.files)
    if ((m1["time"] >= FORBIDDEN[0]) & (m1["time"] < FORBIDDEN[1])).any():
        print("ARRÊT : données de l'OOS vierge fournies.")
        return 2
    cache = {tf: resample(m1, tf) for tf in ("1h", "4h", "15min")}
    cache["daily"] = daily_bars(m1)
    out = Path(args.out)
    (out / "trades").mkdir(parents=True, exist_ok=True)
    allres = {}
    for name, (prep_fn, fn, grid, default) in HYPOTHESES.items():
        prep = prep_fn(m1, cache)
        res = {"parametres_defaut": default, "defaut": {}, "walk_forward": {}}
        for per, (a, b) in DEFAULT_PERIODS.items():
            for cn, c in COSTS.items():
                s = run(m1, prep, fn, default, a, b, c)
                mt = metrics(s)
                res["defaut"][f"{per}_{cn}"] = mt
                pd.DataFrame(s.trades).to_csv(out / "trades" / f"{name}_defaut_{per}_{cn}.csv", index=False)
                print(f"{name:34s} défaut {per:12s} {cn:6s} trades={mt['trades']:4d} PF={mt['profit_factor']} "
                      f"net={mt['rentabilite_pct']}% DD={mt['drawdown_max_pct']}%")
        for cn, c in COSTS.items():
            wf, tr = walk_forward(m1, prep, fn, grid, c)
            res["walk_forward"][cn] = wf
            pd.DataFrame(tr).to_csv(out / "trades" / f"{name}_walkforward_{cn}.csv", index=False)
            print(f"{name:34s} WF {cn:6s} trades={wf['trades']} PF={wf['pf']} net={wf['rentabilite_pct']}% "
                  f"DD={wf['drawdown_max_pct']}% t={wf['t_stat']} trimestres+={wf['trimestres_positifs']}/4")
        res["verdict"] = verdict(res)
        print(f"  → {res['verdict']['decision']}  {res['verdict']['criteres']}")
        allres[name] = res
    (out / "results.json").write_text(json.dumps(allres, indent=2, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
