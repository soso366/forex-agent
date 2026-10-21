"""Strategy Research Lab — lance un lot de backtests Freqtrade et évalue chaque configuration selon CRITERES.md.

Étapes : télécharger les stratégies au commit épinglé → générer les variantes « plafond de durée » →
backtester (Freqtrade) → mesurer par bloc (frais + glissement) → verdict ROBUSTE / FRAGILE / ÉCHEC / ERREUR.
Usage : python crypto_lab/run_batch.py --batch 1
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

LAB = Path(__file__).resolve().parent
UD = Path("user_data")
PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
CAPS = [None, 30, 45, 60]                 # None = version d'origine (référence)
STAKE, WALLET, MAX_OPEN = 50.0, 150.0, 2
FEE = 0.001                               # par ordre
SLIP_RT = 0.001                           # glissement aller-retour ajouté au test de sensibilité (0,05 % x 2)
TIMERANGE = "20230101-20261001"
BLOCKS = {"P1": ("2023-01-01", "2024-07-01"), "P2": ("2024-07-01", "2025-07-01"), "P3": ("2025-07-01", "2026-10-01")}

WRAPPER = '''# Généré par crypto_lab/run_batch.py — seule adaptation : plafond de durée de {cap} min (sortie forcée par ROI -1).
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from {mod} import {cls} as _Base


def _cap_roi(base_roi, cap):
    roi = {{str(k): v for k, v in sorted(((int(k), v) for k, v in (base_roi or {{}}).items())) if k < cap}}
    roi[str(cap)] = -1
    return roi


class {cls}_cap{cap}(_Base):
    minimal_roi = _cap_roi(getattr(_Base, "minimal_roi", {{}}), {cap})
    ignore_roi_if_entry_signal = False
    ignore_roi_if_buy_signal = False
'''


def sh(cmd, log=None, check=True):
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if log:
        Path(log).write_text(r.stdout + "\n" + r.stderr)
    if check and r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:], sep="\n")
    return r


def fetch_repo(name, spec, dest):
    d = dest / name
    if d.exists():
        return d
    d.mkdir(parents=True)
    sh(["git", "-C", str(d), "init", "-q"])
    sh(["git", "-C", str(d), "remote", "add", "origin", spec["url"]])
    sh(["git", "-C", str(d), "fetch", "-q", "--depth", "1", "origin", spec["commit"]])
    sh(["git", "-C", str(d), "checkout", "-q", "FETCH_HEAD"])
    return d


def write_config(exchange):
    cfg = {
        "trading_mode": "spot", "dry_run": True, "dry_run_wallet": WALLET, "stake_currency": "USDT",
        "stake_amount": STAKE, "max_open_trades": MAX_OPEN, "dataformat_ohlcv": "json",
        "entry_pricing": {"price_side": "same", "use_order_book": False, "order_book_top": 1},
        "exit_pricing": {"price_side": "same", "use_order_book": False, "order_book_top": 1},
        "exchange": exchange, "pairlists": [{"method": "StaticPairList"}],
        "bot_name": "crypto_lab", "internals": {"process_throttle_secs": 5},
    }
    Path("config_lab.json").write_text(json.dumps(cfg, indent=1))


def stats(trades, start=None, end=None, slip=SLIP_RT):
    t = [x for x in trades if (start is None or x["open"] >= start) and (end is None or x["open"] < end)]
    n = len(t)
    if n == 0:
        return {"trades": 0}
    r = [x["pr"] - slip for x in t]          # rendement par trade, frais + glissement
    pnl = [STAKE * v for v in r]
    gains, pertes = sum(v for v in pnl if v > 0), -sum(v for v in pnl if v < 0)
    mean = sum(r) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in r) / (n - 1)) if n > 1 else 0.0
    eq, peak, dd = 0.0, 0.0, 0.0
    for v in [STAKE * (x["pr"] - slip) for x in sorted(t, key=lambda x: x["close"])]:
        eq += v
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    by_pair, by_month = {}, {}
    for x, v in zip(t, pnl):
        by_pair[x["pair"]] = by_pair.get(x["pair"], 0) + v
        by_month[x["open"][:7]] = by_month.get(x["open"][:7], 0) + v
    net = sum(pnl)
    return {
        "trades": n,
        "net_usdt_frais_seuls": round(sum(STAKE * x["pr"] for x in t), 2),
        "net_usdt": round(net, 2),
        "gain_moyen_pct": round(100 * mean, 3),
        "taux_gain_pct": round(100 * sum(v > 0 for v in r) / n, 1),
        "profit_factor": round(gains / pertes, 2) if pertes else None,
        "t_stat": round(mean / (sd / math.sqrt(n)), 2) if sd else None,
        "drawdown_max_usdt": round(dd, 2),
        "duree_moy_min": round(sum(x["dur"] for x in t) / n, 1),
        "part_sortie_plafond_pct": round(100 * sum(x["reason"] == "roi" and x["dur"] >= x.get("cap", 10**9) for x in t) / n, 1),
        "part_max_paire": round(max(by_pair.values()) / net, 2) if net > 0 else None,   # part du gain net
        "part_max_mois": round(max(by_month.values()) / net, 2) if net > 0 else None,
        "par_paire_usdt": {k: round(v, 2) for k, v in sorted(by_pair.items())},
    }


def verdict(s, block_names=BLOCKS):
    blocks = [s[b] for b in block_names]
    g = s["global"]
    if g.get("trades", 0) == 0:
        return "ÉCHEC", ["aucun trade"]
    why = []
    if any(b.get("trades", 0) < 100 for b in blocks):
        why.append("moins de 100 trades sur un bloc")
    if any(b.get("net_usdt", -1) <= 0 for b in blocks):
        why.append("perdante sur au moins un bloc")
    if (g.get("profit_factor") or 0) < 1.15:
        why.append("profit factor < 1,15")
    if (g.get("t_stat") or 0) < 2.0:
        why.append("t < 2 (pas distinguable du hasard)")
    if g["net_usdt"] > 0 and max(g.get("part_max_paire") or 0, g.get("part_max_mois") or 0) > 0.5:
        why.append("gain concentré (>50 % sur une paire ou un mois)")
    if g["drawdown_max_usdt"] > 0.2 * WALLET:
        why.append("drawdown > 20 % du capital")
    if not why:
        return "ROBUSTE", []
    return ("FRAGILE" if g["net_usdt"] > 0 else "ÉCHEC"), why


PORT = [("np.NAN", "np.nan")]   # portage mécanique NumPy 2 (même valeur), aucune logique modifiée


def run_one(job, cand, exchange, logs):
    """Un passage du plan run.yaml : backtests + audit éventuel. Renvoie la liste de résultats."""
    ids = job.get("ids")
    todo = [c for c in cand["candidates"] if c["verdict"] == "TEST" and c.get("file")
            and ((ids and c["id"] in ids) or (not ids and c.get("batch") == job.get("batch")))]
    ex = dict(exchange, pair_whitelist=job["pairs"])
    trange = job.get("timerange", TIMERANGE)
    blocks = job.get("blocks", BLOCKS)
    write_config(ex)
    sdir = UD / "strategies"
    sdir.mkdir(parents=True, exist_ok=True)
    out = []
    for c in todo:
        repo = fetch_repo(c["repo"], cand["repos"][c["repo"]], Path("ext"))
        src = repo / c["file"]
        code = src.read_text()
        ports = [a for a, b in PORT if a in code]
        for a, b in PORT:
            code = code.replace(a, b)
        (sdir / src.name).write_text(code)
        names = []
        for cap in CAPS:
            if cap is None:
                names.append(c["name"])
                continue
            (sdir / f"{c['name']}_cap{cap}.py").write_text(WRAPPER.format(mod=src.stem, cls=c["name"], cap=cap))
            names.append(f"{c['name']}_cap{cap}")
        res_dir = UD / "backtest_results"
        if res_dir.exists():
            shutil.rmtree(res_dir)
        res_dir.mkdir(parents=True)
        tf = c.get("timeframe", "5m")
        r = sh(["freqtrade", "backtesting", "-c", "config_lab.json", "--userdir", str(UD), "--timerange", trange,
                "--fee", str(FEE), "--timeframe", tf, "--export", "trades", "--cache", "none", "--strategy-list", *names],
               log=logs / f"{job['label']}_{c['id']}_{c['name']}.log")
        if r.returncode != 0:
            err = (r.stderr or r.stdout).strip().splitlines()[-5:]
            out.append({"id": c["id"], "strategie": c["name"], "verdict": "ERREUR", "erreur": err})
            continue
        audit = None
        if job.get("audit"):
            ra = sh(["freqtrade", "lookahead-analysis", "-c", "config_lab.json", "--userdir", str(UD), "--strategy", c["name"],
                     "--timeframe", tf, "--timerange", "20250101-20250401", "--fee", str(FEE)],
                    log=logs / f"{job['label']}_{c['id']}_lookahead.log")
            txt = (ra.stdout + ra.stderr)
            low = txt.lower()
            if ra.returncode != 0:
                audit = "audit impossible (voir log)"
            elif "has_bias" in low or "bias" in low:
                rows = [l for l in txt.splitlines() if c["name"] in l and "|" in l]
                audit = "BIAIS DÉTECTÉ" if any("true" in l.lower() for l in rows) else "aucun biais détecté"
            else:
                audit = "résultat non lu (voir log)"
        from freqtrade.data.btanalysis import load_backtest_data
        for name, cap in zip(names, CAPS):
            df = load_backtest_data(res_dir, strategy=name)
            trades = [{"pair": p, "pr": float(pr), "open": str(o)[:10], "close": str(cl), "dur": float(d),
                       "reason": str(er), "cap": cap or 10**9}
                      for p, pr, o, cl, d, er in zip(df["pair"], df["profit_ratio"], df["open_date"], df["close_date"],
                                                     df["trade_duration"], df["exit_reason"])]
            s = {"global": stats(trades)}
            for b, (d0, d1) in blocks.items():
                s[b] = stats(trades, d0, d1)
            if job.get("stress_slip_rt"):
                s["stress"] = stats(trades, slip=job["stress_slip_rt"])
            v, why = verdict(s, blocks)
            if audit == "BIAIS DÉTECTÉ":
                v, why = "ÉCHEC", ["biais d'anticipation détecté"] + why
            out.append({"id": c["id"], "strategie": c["name"], "plafond_min": cap, "verdict": v, "raisons": why,
                        "audit_biais": audit, "portage": ports, "mesures": s})
            print(name, v, why, audit, flush=True)
    return out


def table(label, rows, blocks=BLOCKS):
    lines = [f"# {label} — résultats (frais 0,10 %/ordre + glissement 0,05 %/ordre)", "",
             "| Stratégie | Plafond | Trades | Net USDT | Gain moyen % | Taux de gain | PF | t | DD max | " + " | ".join(blocks) + " | Stress | Audit biais | Verdict |",
             "|---|---|---|---|---|---|---|---|---|" + "---|" * len(blocks) + "---|---|---|"]
    for r in rows:
        if r["verdict"] == "ERREUR":
            lines.append(f"| {r['strategie']} | — | — | — | — | — | — | — | — | " + "— | " * len(blocks) + f"— | — | ERREUR : {' / '.join(r['erreur'])[:200]} |")
            continue
        g, m = r["mesures"]["global"], r["mesures"]
        cap = f"{r['plafond_min']} min" if r["plafond_min"] else "origine"
        stress = m.get("stress", {}).get("net_usdt", "—")
        lines.append(f"| {r['strategie']} | {cap} | {g.get('trades', 0)} | {g.get('net_usdt', 0)} | {g.get('gain_moyen_pct')} | "
                     f"{g.get('taux_gain_pct')} % | {g.get('profit_factor')} | {g.get('t_stat')} | {g.get('drawdown_max_usdt')} | "
                     + " | ".join(str(m[b].get('net_usdt', 0)) for b in blocks) + f" | {stress} | "
                     f"{r.get('audit_biais') or '—'} | **{r['verdict']}** {'; '.join(r['raisons'])} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=str(LAB / "run.yaml"))
    a = ap.parse_args()
    cand = yaml.safe_load((LAB / "candidates.yaml").read_text())
    plan = yaml.safe_load(Path(a.plan).read_text())["runs"]
    exchange = json.loads(Path("exchange_choice.json").read_text())
    logs = Path("logs")
    logs.mkdir(exist_ok=True)
    res = LAB / "results"
    res.mkdir(exist_ok=True)
    for job in plan:
        rows = run_one(job, cand, exchange, logs)
        out = {"label": job["label"], "plan": job, "conditions": {"mise_usdt": STAKE, "capital": WALLET,
               "positions_max": MAX_OPEN, "frais_par_ordre": FEE, "glissement_aller_retour": SLIP_RT,
               "periode": job.get("timerange", TIMERANGE), "blocs": job.get("blocks", BLOCKS), "exchange": exchange["name"]}, "resultats": rows}
        (res / f"{job['label']}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
        md = table(job["label"], rows, job.get("blocks", BLOCKS))
        (res / f"{job['label']}.md").write_text(md)
        print(md, flush=True)


if __name__ == "__main__":
    main()
