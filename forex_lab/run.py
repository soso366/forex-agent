"""Lance le lot 1 du Forex Strategy Research Lab et applique les critères de CRITERES.md.

Usage : python -m forex_lab.run --data <dossier des branches forex-data> [--only F01 F03]
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .engine import REALISTIC, Costs, Simulator, load_m1, resample, run_portfolio, signal_events
from .strategies import BAR_STRATEGIES, f03_events

LAB = Path(__file__).resolve().parent
BLOCKS = {"B1": ("2024-09-01", "2025-03-01"), "B2": ("2025-03-01", "2025-09-01"),
          "B3": ("2025-09-01", "2026-03-01"), "B4": ("2026-03-01", "2026-09-01")}
STRESS = 0.5


def tstat(x):
    x = np.asarray(x, float)
    if len(x) < 2 or x.std(ddof=1) == 0:
        return None
    return round(float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))), 2)


def stats(trades):
    if not trades:
        return {"trades": 0}
    df = pd.DataFrame([{"pair": t.pair, "t": t.entry_time, "pips": t.pips, "dur": (t.exit_time - t.entry_time).total_seconds() / 60,
                        "reason": t.reason} for t in trades])
    x = df["pips"].to_numpy()
    g, l = x[x > 0].sum(), -x[x < 0].sum()
    daily = df.groupby(df["t"].dt.date)["pips"].sum()
    out = {"trades": int(len(x)), "pips_total": round(float(x.sum()), 1), "pips_moyen": round(float(x.mean()), 3),
           "taux_gain_pct": round(100 * float((x > 0).mean()), 1), "profit_factor": round(float(g / l), 2) if l else None,
           "t_trades": tstat(x), "t_jours": tstat(daily.to_numpy()), "jours": int(len(daily)),
           "pips_moyen_stress": round(float(x.mean() - STRESS), 3), "duree_moy_min": round(float(df["dur"].mean()), 1),
           "sorties": df["reason"].value_counts().to_dict(),
           "par_paire_pips": {k: round(float(v), 1) for k, v in df.groupby("pair")["pips"].sum().items()}}
    for b, (d0, d1) in BLOCKS.items():
        m = (df["t"] >= pd.Timestamp(d0, tz="UTC")) & (df["t"] < pd.Timestamp(d1, tz="UTC"))
        out[b] = {"trades": int(m.sum()), "pips_moyen": round(float(x[m].mean()), 3) if m.any() else None}
    net = x.sum()
    out["part_max_paire"] = round(float(max(out["par_paire_pips"].values()) / net), 2) if net > 0 and len(out["par_paire_pips"]) > 1 else None
    return out


def verdict(s):
    if s.get("trades", 0) == 0:
        return "ÉCHEC", ["aucun trade"]
    why = []
    if s["trades"] < 80:
        why.append("moins de 80 trades")
    if sum(1 for b in BLOCKS if (s[b]["pips_moyen"] or -1) > 0) < 3:
        why.append("positive sur moins de 3 blocs sur 4")
    if (s["profit_factor"] or 0) < 1.15:
        why.append("profit factor < 1,15")
    if (s["t_trades"] or 0) < 2.5 or (s["t_jours"] or 0) < 2.0:
        why.append("pas distinguable du hasard (t)")
    if s["pips_moyen_stress"] <= 0:
        why.append("négative avec +0,5 pip de coût")
    if s["part_max_paire"] is not None and s["part_max_paire"] > 0.6:
        why.append("gain concentré sur une paire")
    if not why:
        return "ROBUSTE", []
    return ("FRAGILE" if s["pips_moyen"] > 0 else "ÉCHEC"), why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--label", default="lot_1")
    ap.add_argument("--costs", choices=["spread", "realistic"], default="realistic",
                    help="spread : spread bid/ask seul (lot 1 d'origine) ; realistic : + commission 3 $/lot/côté + 0,1 pip de glissement")
    ap.add_argument("--max-open", type=int, default=2, help="positions simultanées max, toutes paires (0 = sans limite)")
    a = ap.parse_args()
    cand = {c["id"]: c for c in yaml.safe_load((LAB / "candidates.yaml").read_text())["candidates"]}
    todo = [i for i in cand if cand[i]["verdict"] == "TEST" and (not a.only or i in a.only)]
    pairs = sorted({p for i in todo for p in cand[i]["paires"]})
    m1, sims, bars = {}, {}, {}
    for p in pairs:
        t0 = time.time()
        m1[p] = load_m1(Path(a.data), p)
        sims[p] = Simulator(p, m1[p], REALISTIC if a.costs == "realistic" else Costs())
        print(f"{p}: {len(m1[p]):,} minutes ({time.time() - t0:.0f} s)", flush=True)
    start = max(m.index[0] for m in m1.values())
    end = min(m.index[-1] for m in m1.values())
    results = []
    for cid in todo:
        c = cand[cid]
        for version in ("exact", "projet"):
            t0 = time.time()
            events = []
            for p in c["paires"]:
                if cid == "F03":
                    events += f03_events(p, start, end, version)
                else:
                    fn, tf, r_exact, r_projet = BAR_STRATEGIES[cid]
                    key = (p, tf)
                    if key not in bars:
                        bars[key] = resample(m1[p], tf)
                    b = bars[key]
                    lg, sh, el, es = fn(b, p)
                    events += signal_events(p, b, lg.fillna(False).to_numpy(), sh.fillna(False).to_numpy(),
                                            r_exact if version == "exact" else r_projet, tf,
                                            None if el is None else el.fillna(False).to_numpy(),
                                            None if es is None else es.fillna(False).to_numpy(), cid)
            trades = run_portfolio(events, sims, a.max_open or None)
            s = stats(trades)
            v, why = verdict(s)
            results.append({"id": cid, "nom": c["nom"], "version": version, "verdict": v, "raisons": why, "mesures": s})
            print(f"{cid} {version}: {s.get('trades')} trades, {s.get('pips_moyen')} pips/trade, PF {s.get('profit_factor')}, "
                  f"t {s.get('t_trades')}/{s.get('t_jours')} → {v} ({time.time() - t0:.0f} s)", flush=True)
    out = LAB / "results"
    out.mkdir(exist_ok=True)
    meta = {"label": a.label, "couts": a.costs, "positions_max": a.max_open, "periode": [str(start), str(end)], "blocs": BLOCKS, "stress_pips": STRESS, "resultats": results}
    (out / f"{a.label}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False, default=str))
    lines = [f"# {a.label} — stratégies Forex open source (Dukascopy bid/ask, sept. 2024 → août 2026)", "",
             "| ID | Stratégie | Version | Trades | Pips/trade | Taux de gain | PF | t (trades / jours) | B1 | B2 | B3 | B4 | Stress +0,5 | Verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        s = r["mesures"]
        if not s.get("trades"):
            lines.append(f"| {r['id']} | {r['nom']} | {r['version']} | 0 | — | — | — | — | — | — | — | — | — | **{r['verdict']}** |")
            continue
        lines.append(f"| {r['id']} | {r['nom']} | {r['version']} | {s['trades']} | {s['pips_moyen']} | {s['taux_gain_pct']} % | "
                     f"{s['profit_factor']} | {s['t_trades']} / {s['t_jours']} | " +
                     " | ".join(str(s[b]['pips_moyen']) for b in BLOCKS) +
                     f" | {s['pips_moyen_stress']} | **{r['verdict']}** {'; '.join(r['raisons'])} |")
    (out / f"{a.label}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
