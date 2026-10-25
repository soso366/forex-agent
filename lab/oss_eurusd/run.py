"""Lance tous les backtests du protocole et écrit results/oss_eurusd/.

Usage : python run.py <fichiers EURUSD*.csv.gz ...> [--out DOSSIER]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from engine import Costs, Sim, load_m1, metrics, resample
from strategies import CONTROLS, STRATEGIES

PERIODS = {
    "entrainement": ("2024-09-01", "2025-09-01"),
    "validation": ("2025-09-01", "2026-09-01"),
}
FORBIDDEN = ("2023-09-01", "2024-09-01")      # OOS vierge du projet : jamais lu
COSTS = {
    "base": Costs("base", commission_per_lot=7.0, slippage_pips=0.2),
    "stress": Costs("stress", commission_per_lot=9.0, slippage_pips=0.5),
}


def run_one(m1, bars_cache, name, tf, fn, period, costs, capital):
    a, b = (pd.Timestamp(x, tz="UTC") for x in PERIODS[period])
    bars = bars_cache[tf]
    i0 = int(bars["time"].searchsorted(a))
    i1 = int(bars["time"].searchsorted(b))
    m_end = int(m1["time"].searchsorted(b))
    sim = Sim(m1, costs, capital, i_end=m_end)
    fn(m1, bars, max(i0, 2), i1, sim)
    sim.close_end()
    res = metrics(sim)
    res.update(strategie=name, periode=period, couts=costs.name, capital=capital)
    return res, sim.trades


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default="results/oss_eurusd")
    args = ap.parse_args(argv)
    m1 = load_m1(args.files)
    fa, fb = (pd.Timestamp(x, tz="UTC") for x in FORBIDDEN)
    if ((m1["time"] >= fa) & (m1["time"] < fb)).any():
        print("ARRÊT : des données de la période OOS vierge (09/2023-08/2024) ont été fournies.")
        return 2
    print(f"M1 chargées : {len(m1)} minutes, {m1['time'].iloc[0]} → {m1['time'].iloc[-1]}")
    bars_cache = {tf: resample(m1, tf) for tf in {"1h", "5min"}}
    out = Path(args.out)
    (out / "trades").mkdir(parents=True, exist_ok=True)
    rows = []
    jobs = [(n, *v, True) for n, v in STRATEGIES.items()] + [(n, *v, False) for n, v in CONTROLS.items()]
    for name, tf, fn, main_strat in jobs:
        for period in PERIODS:
            for cname, costs in COSTS.items():
                if not main_strat and cname != "base":
                    continue
                res, trades = run_one(m1, bars_cache, name, tf, fn, period, costs, 10_000.0)
                res["controle"] = not main_strat
                rows.append(res)
                pd.DataFrame(trades).to_csv(out / "trades" / f"{name}_{period}_{cname}.csv", index=False)
                print(f"{name:42s} {period:12s} {cname:6s} trades={res['trades']:4d} PF={res['profit_factor']} "
                      f"net={res['rentabilite_pct']}% DD={res['drawdown_max_pct']}%")
            if main_strat:     # faisabilité avec le petit capital du projet (150)
                res, _ = run_one(m1, bars_cache, name, tf, fn, period, COSTS["base"], 150.0)
                res["controle"] = True
                res["strategie"] = name + "_capital_150"
                rows.append(res)
    (out / "results.json").write_text(json.dumps(rows, indent=2, default=str, ensure_ascii=False))
    print(f"Écrit : {out/'results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
