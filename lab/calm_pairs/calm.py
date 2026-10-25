"""H-C : retour à la moyenne avec stop strict sur AUDCAD, NZDCAD, AUDNZD (voir PROTOCOLE.md).

Usage : python calm.py <dossier_des_csv_gz> [--out DOSSIER]
Fichiers attendus : <SYMBOLE>_<période>.csv.gz (artifacts du workflow export-crosses.yml).
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "oss_eurusd"))
sys.path.insert(0, str(HERE.parent / "traders_eurusd"))
from engine import POINT, TICK_VALUE, Costs, atr_mt5, bands_mt5, load_m1, metrics, normalize_lot_floor, resample, rsi_mt5  # noqa: E402
from wf import DEFAULT_PERIODS, FORBIDDEN, run, verdict, walk_forward  # noqa: E402

PAIRS = {"AUDCAD": 1.37, "NZDCAD": 1.37, "AUDNZD": 1.70}   # 1 USD en devise de cotation (commission)
GRID = [dict(k=k, r=r, s=s) for k, r, s in product((2.0, 2.5), (25, 30), (1.5, 2.5))]
DEFAULT = dict(k=2.0, r=30, s=1.5)


def run_hc(sim, bars, i0, i1, p):
    c = bars["bid_close"].to_numpy()
    bbu, bbm, bbl = bands_mt5(c, 20, p["k"])
    rsi = rsi_mt5(c, 14)
    atr = atr_mt5(bars["bid_high"].to_numpy(), bars["bid_low"].to_numpy(), c, 14)
    t = bars["time"]
    start = bars["start"].to_numpy()
    for b in range(max(i0, 2), i1):
        m0 = int(start[b])
        sim.advance_to(m0)
        sim.mark(m0)
        if sim.pos is not None:
            if t.iloc[b] - sim.pos.t_entry >= pd.Timedelta(hours=48):
                sim.close_market(m0, "sortie_48h")
            continue
        if np.isnan(bbu[b - 1]) or np.isnan(rsi[b - 1]) or np.isnan(atr[b - 1]):
            continue
        sell = c[b - 1] > bbu[b - 1] and rsi[b - 1] > 100 - p["r"]
        buy = c[b - 1] < bbl[b - 1] and rsi[b - 1] < p["r"]
        if not (buy or sell):
            continue
        side = 1 if buy else -1
        quote = sim.ao[m0] if side > 0 else sim.bo[m0]
        sl_dist = p["s"] * atr[b - 1]
        tp_dist = (bbm[b - 1] - quote) * side
        if sl_dist <= 0 or tp_dist < 0.5 * sl_dist:
            continue
        lots = normalize_lot_floor(sim.balance * 0.01 / ((sl_dist / POINT) * TICK_VALUE))
        if lots <= 0:
            sim.refused_lot += 1
            continue
        sim.open(side, m0, quote, round(quote - side * sl_dist, 5), round(bbm[b - 1], 5), lots, f"HC rsi={rsi[b-1]:.0f}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", default="results/calm_pairs")
    a = ap.parse_args(argv)
    out = Path(a.out)
    (out / "trades").mkdir(parents=True, exist_ok=True)
    allres = {}
    for pair, fx in PAIRS.items():
        files = sorted(Path(a.folder).glob(f"{pair}_*.csv.gz"))
        if not files:
            print(f"{pair} : aucune donnée")
            continue
        m1 = load_m1([str(f) for f in files])
        if ((m1["time"] >= FORBIDDEN[0]) & (m1["time"] < FORBIDDEN[1])).any():
            print("ARRÊT : données hors fenêtre autorisée")
            return 2
        bars = resample(m1, "1h")
        costs = {"base": Costs("base", 7.0 * fx, 0.2), "stress": Costs("stress", 9.0 * fx, 0.5)}
        res = {"parametres_defaut": DEFAULT, "defaut": {}, "walk_forward": {}}
        for per, (s, e) in DEFAULT_PERIODS.items():
            for cn, cst in costs.items():
                sim = run(m1, bars, run_hc, DEFAULT, s, e, cst)
                mt = metrics(sim)
                res["defaut"][f"{per}_{cn}"] = mt
                pd.DataFrame(sim.trades).to_csv(out / "trades" / f"{pair}_defaut_{per}_{cn}.csv", index=False)
                print(f"{pair} défaut {per:12s} {cn:6s} trades={mt['trades']:4d} PF={mt['profit_factor']} "
                      f"net={mt['rentabilite_pct']}% DD={mt['drawdown_max_pct']}% réussite={mt['taux_reussite_pct']}%")
        for cn, cst in costs.items():
            wf, tr = walk_forward(m1, bars, run_hc, GRID, cst)
            res["walk_forward"][cn] = wf
            pd.DataFrame(tr).to_csv(out / "trades" / f"{pair}_walkforward_{cn}.csv", index=False)
            print(f"{pair} WF {cn:6s} trades={wf['trades']} PF={wf['pf']} net={wf['rentabilite_pct']}% "
                  f"DD={wf['drawdown_max_pct']}% t={wf['t_stat']} trimestres+={wf['trimestres_positifs']}/4")
        res["verdict"] = verdict(res)
        print(f"  → {pair} : {res['verdict']['decision']}")
        allres[pair] = res
    (out / "results.json").write_text(json.dumps(allres, indent=2, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
