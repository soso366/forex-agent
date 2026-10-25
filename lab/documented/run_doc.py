"""Exécute le protocole des 10 méthodes documentées (PROTOCOLE.md) et écrit results/documented/.

Usage : python run_doc.py <fichiers EURUSD_*.csv.gz ...> [--out DOSSIER] [--only M1_turtle_S1,...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dsim import Book, Costs, daily, hourly, load_m1, summarize
from methods import METHODS

TS = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731
FORBIDDEN = (TS("2023-09-01"), TS("2024-09-01"))
PERIODS = {"entrainement": (TS("2015-01-01"), TS("2021-01-01")),
           "validation_1": (TS("2021-01-01"), TS("2023-09-01")),
           "validation_2": (TS("2024-09-01"), TS("2026-09-01"))}
YEARS = [(str(y), TS(f"{y}-01-01"), TS(f"{y + 1}-01-01")) for y in range(2015, 2023)] + \
        [("2023 (jan-août)", TS("2023-01-01"), TS("2023-09-01")), ("2024 (sept-déc)", TS("2024-09-01"), TS("2025-01-01")),
         ("2025", TS("2025-01-01"), TS("2026-01-01")), ("2026 (jan-août)", TS("2026-01-01"), TS("2026-09-01"))]
COSTS = {"base": Costs("base", 7.0, 0.2), "stress": Costs("stress", 9.0, 0.5)}


def run(h, d, fn, params, a, b, costs):
    i0, i1 = int(h["time"].searchsorted(a)), int(h["time"].searchsorted(b))
    book = Book(costs)
    if i1 - i0 < 24:
        return None, book
    fn(h, d, i0, i1, book, params)
    last = h.iloc[i1 - 1]
    book.close_all(last.bc, last.ac - last.bc, last.time, "fin_de_periode")
    return summarize(book, a, b), book


def pooled(books):
    p = np.concatenate([np.array([t["pnl"] for t in bk.trades]) for bk in books if bk.trades] or [np.array([])])
    if len(p) == 0:
        return {"trades": 0, "pf": None, "t_stat": None, "net_usd": 0.0}
    gp, gl = p[p > 0].sum(), -p[p < 0].sum()
    t = float(p.mean() / (p.std(ddof=1) / math.sqrt(len(p)))) if len(p) > 2 and p.std(ddof=1) > 0 else None
    return {"trades": int(len(p)), "pf": round(gp / gl, 3) if gl > 0 else None,
            "t_stat": round(t, 2) if t is not None else None, "net_usd": round(float(p.sum()), 2)}


def variants(params, keys):
    out = []
    for k in keys:
        for f in (0.75, 1.25):
            q = dict(params)
            v = params[k] * f
            q[k] = max(1, int(round(v))) if isinstance(params[k], int) else round(v, 3)
            if q[k] != params[k]:
                out.append((f"{k}×{f}", q))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default="results/documented")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    m1 = load_m1(a.files)
    if ((m1["time"] >= FORBIDDEN[0]) & (m1["time"] < FORBIDDEN[1])).any():
        print("ARRÊT : données de l'OOS vierge (09/2023-08/2024) fournies.")
        return 2
    print(f"M1 : {len(m1):,} minutes, {m1['time'].iloc[0]} → {m1['time'].iloc[-1]}")
    h = hourly(m1)
    d = daily(h)
    del m1
    out = Path(a.out)
    (out / "trades").mkdir(parents=True, exist_ok=True)
    only = set(filter(None, a.only.split(",")))
    allres = {}
    for name, (fn, params, keys) in METHODS.items():
        if only and name not in only:
            continue
        res = {"parametres": params, "periodes": {}, "annees": {}, "trimestres_validation": {}, "stabilite": {}}
        books = {}
        for per, (s, e) in PERIODS.items():
            for cn, c in COSTS.items():
                m, bk = run(h, d, fn, params, s, e, c)
                res["periodes"][f"{per}_{cn}"] = m
                books[(per, cn)] = bk
                if m:
                    pd.DataFrame(bk.trades).to_csv(out / "trades" / f"{name}_{per}_{cn}.csv", index=False)
        for lbl, s, e in YEARS:
            m, _ = run(h, d, fn, params, s, e, COSTS["base"])
            res["annees"][lbl] = m
        vb = [books[("validation_1", "base")], books[("validation_2", "base")]]
        vs = [books[("validation_1", "stress")], books[("validation_2", "stress")]]
        for bk in vb:
            for t in bk.trades:
                q = f"{pd.Timestamp(t['t_exit']).year}T{pd.Timestamp(t['t_exit']).quarter}"
                res["trimestres_validation"][q] = round(res["trimestres_validation"].get(q, 0.0) + t["pnl"], 2)
        res["validation_reunie_base"] = pooled(vb)
        res["validation_reunie_stress"] = pooled(vs)
        dds = [res["periodes"][f"{p}_base"]["drawdown_max_pct"] for p in ("validation_1", "validation_2") if res["periodes"][f"{p}_base"]]
        res["validation_reunie_base"]["drawdown_max_pct"] = max(dds) if dds else None
        ok_var = []
        for lbl, q in variants(params, keys):
            bks = [run(h, d, fn, q, *PERIODS[p], COSTS["base"])[1] for p in ("validation_1", "validation_2")]
            pv = pooled(bks)
            res["stabilite"][lbl] = pv
            ok_var.append((pv["pf"] or 0) > 1)
        yrs = [v for v in res["annees"].values() if v]
        pos_years = sum(1 for v in yrs if v["rentabilite_pct"] > 0)
        tr = res["periodes"]["entrainement_base"]
        vr = res["validation_reunie_base"]
        crit = {
            "pf_1_30": (vr["pf"] or 0) >= 1.30,
            "stress_positif": res["validation_reunie_stress"]["net_usd"] > 0,
            "60_trades": vr["trades"] >= 60,
            "dd_15": vr["drawdown_max_pct"] is not None and vr["drawdown_max_pct"] <= 15,
            "60pct_annees_positives": bool(yrs) and pos_years / len(yrs) >= 0.6,
            "entrainement_positif": bool(tr) and tr["rentabilite_pct"] > 0,
            "stabilite_70pct": (not ok_var) or sum(ok_var) / len(ok_var) >= 0.7,
            "t_stat_2_6": (vr["t_stat"] or 0) >= 2.6,
        }
        res["annees_positives"] = f"{pos_years}/{len(yrs)}"
        res["criteres"] = {k: bool(v) for k, v in crit.items()}
        res["decision"] = "PASSE" if all(crit.values()) else "REJETÉE"
        allres[name] = res
        print(f"{name:26s} entr={tr and tr['rentabilite_pct']}% PF={tr and tr['pf']} | valid PF={vr['pf']} trades={vr['trades']} "
              f"t={vr['t_stat']} DD={vr['drawdown_max_pct']} stress={res['validation_reunie_stress']['net_usd']} "
              f"années+={res['annees_positives']} stab={sum(ok_var)}/{len(ok_var)} → {res['decision']}")
        (out / "results.json").write_text(json.dumps(allres, indent=2, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
