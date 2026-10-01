"""Ligne de commande.

  python -m forex_agent run-once            # un cycle (pour cron : */5 * * * *)
  python -m forex_agent loop                # boucle autonome toutes les 5 minutes
  python -m forex_agent replay --days 5     # rejoue N jours de cycles sur données historiques/synthétiques
  python -m forex_agent report              # bilan du journal
  python -m forex_agent reset               # repart de 50 € (efface le journal paper)
  python -m forex_agent data-download       # Dukascopy M1 BID+ASK → data/m1/<SYMBOL>.csv (6 derniers mois complets)
  python -m forex_agent data-validate       # relit et valide les CSV
  python -m forex_agent backtest            # rejoue la V2 inchangée sur toute la période CSV + rapport
  python -m forex_agent pipeline            # tout en une fois (utilisé par le déploiement cloud)
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .config import ROOT, deep_merge, load_config, resolve_path
from .fx import conversion_symbols
from .scheduler import loop, replay, run_once


def report(cfg: dict) -> str:
    db = sqlite3.connect(str(resolve_path(cfg, "db")))
    db.row_factory = sqlite3.Row
    acc = db.execute("SELECT * FROM account WHERE id=1").fetchone()
    if acc is None:
        return "Journal vide."
    trades = [dict(r) for r in db.execute("SELECT * FROM trades WHERE status='closed' ORDER BY exit_time")]
    open_ = db.execute("SELECT COUNT(*) FROM trades WHERE status='open'").fetchone()[0]
    ncycles = db.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
    errors = db.execute("SELECT COUNT(*) FROM cycles WHERE error IS NOT NULL").fetchone()[0]
    decisions = Counter(r[0] for r in db.execute("SELECT decision FROM market_snapshots"))
    regimes = Counter(r[0] for r in db.execute("SELECT regime FROM market_snapshots WHERE regime IS NOT NULL"))
    ideas = db.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
    lines = [
        f"Capital : {acc['starting_capital']:.2f} -> {acc['balance']:.2f} {acc['currency']}"
        f" ({(acc['balance'] / acc['starting_capital'] - 1) * 100:+.1f} %) | plus haut {acc['peak_equity']:.2f}",
        f"Cycles journalisés : {ncycles} (erreurs : {errors}) | positions ouvertes : {open_} | idées notées : {ideas}",
        f"Décisions par paire : {dict(decisions)}",
        f"Régimes observés : {dict(regimes)}",
    ]
    if trades:
        df = pd.DataFrame(trades)
        wins = (df["pnl_eur"] > 0).mean() * 100
        gp, gl = df.loc[df.pnl_eur > 0, "pnl_eur"].sum(), -df.loc[df.pnl_eur < 0, "pnl_eur"].sum()
        eq = pd.concat([pd.Series([acc["starting_capital"]]), df["balance_after"]])
        max_dd = ((eq.cummax() - eq) / eq.cummax()).max() * 100
        lines += [
            f"Trades : {len(df)} | gagnants {wins:.0f} % | PnL {df.pnl_eur.sum():+.2f} | "
            f"profit factor {gp / gl if gl else float('inf'):.2f} | drawdown max {max_dd:.1f} %",
            f"Durée moyenne {df.duration_min.mean():.1f} min | max {df.duration_min.max():.1f} min | "
            f"cas SL/TP ambigus {int(df.intrabar_ambiguous.sum())}",
            f"Risque par trade : {df.risk_eur.min():.3f} à {df.risk_eur.max():.3f} | unités {df.units.min():.0f} à {df.units.max():.0f}",
        ]
        if "r_multiple" in df and df.r_multiple.notna().any():
            lines.append(f"Espérance {df.r_multiple.mean():+.2f} R/trade | MFE moyen {df.mfe_r.mean():.2f} R | "
                         f"MAE moyen {df.mae_r.mean():.2f} R")

        def block(title, col):
            if col not in df or df[col].isna().all():
                return
            lines.append(title)
            for key, g in df.groupby(df[col].fillna("—")):
                exp = f" | {g.r_multiple.mean():+.2f} R" if g.r_multiple.notna().any() else ""
                lines.append(f"  {str(key):20s} {len(g):3d} trades | {(g.pnl_eur > 0).mean() * 100:3.0f} % gagnants"
                             f" | PnL {g.pnl_eur.sum():+.2f}{exp}")

        block("Par stratégie :", "strategy")
        block("Par régime à l'entrée (P(gain | régime)) :", "regime")
        block("Par session :", "session")
        block("Par killzone :", "killzone")
        lines.append("Échantillon trop petit pour conclure." if len(df) < 100 else
                     "Échantillon ≥ 100 trades : comparer aussi hors échantillon avant de valider.")
        lines.append("Sorties : " + str(dict(Counter(r.split(" ")[0].split(":")[0] for r in df.exit_reason))))
        lines.append("Derniers trades :")
        for t in trades[-5:]:
            lines.append(f"  #{t['id']} {t['exit_time'][:16]} {t['symbol']} {t['direction']} {t['strategy']} "
                         f"{t['duration_min']:.0f} min PnL {t['pnl_eur']:+.3f} -> {t['balance_after']:.2f}")
    db.close()
    return "\n".join(lines)


def default_period(today: date | None = None) -> tuple[date, date]:
    """Règle fixe, décidée AVANT de voir les résultats : les 6 derniers mois civils complets."""
    today = today or date.today()
    first_this_month = today.replace(day=1)
    end = first_this_month - timedelta(days=1)
    y, m = first_this_month.year, first_this_month.month - 6
    while m <= 0:
        y, m = y - 1, m + 12
    return date(y, m, 1), end


def _csv_dir(cfg: dict) -> Path:
    d = Path(cfg["data"]["csv_dir"])
    return d if d.is_absolute() else ROOT / d


def code_fingerprint(cfg: dict) -> str:
    """Empreinte du code + de la configuration : une reprise n'est permise qu'à l'identique."""
    import hashlib
    h = hashlib.sha256()
    for f in sorted((ROOT / "forex_agent").rglob("*.py")):
        h.update(f.read_bytes())
    h.update(json.dumps(cfg, sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def run_backtest(cfg: dict, warmup_days: int = 7, out_dir: Path | None = None, progress: bool = True,
                 resume: bool = False, stop_at: float | None = None, state: dict | None = None) -> str:
    """Rejeu de la V2 inchangée sur toute la période CSV disponible (aucune sélection de période).
    resume=True : reprend après une interruption, uniquement si code, config et données sont identiques."""
    from .backtest_report import build_report
    from .data.providers import CSVProvider
    bt_dir = Path(out_dir) if out_dir else ROOT / "data" / "backtest"
    bt_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = code_fingerprint(cfg)
    cfg = deep_merge(cfg, {"data": {"provider": "csv"},
                           "paths": {"db": str(bt_dir / "journal.sqlite"), "jsonl": str(bt_dir / "cycles.jsonl"),
                                     "kill_switch": str(bt_dir / "KILL_SWITCH"), "lock": str(bt_dir / "lock")}})
    symbols = list(cfg["symbols"]) + [s for s in conversion_symbols(cfg["symbols"], cfg["account"]["currency"])
                                      if s not in cfg["symbols"]]
    prov = CSVProvider(symbols, _csv_dir(cfg))
    first, last = prov.time_range()
    start = (pd.Timestamp(first).normalize() + pd.Timedelta(days=warmup_days)).to_pydatetime()
    meta = {"code_and_config": fingerprint, "data_first": str(first), "data_last": str(last),
            "warmup_days": warmup_days, "symbols": cfg["symbols"],
            "csv_sizes": {s: (_csv_dir(cfg) / f"{s}.csv").stat().st_size for s in symbols}}
    meta_path = bt_dir / "run_meta.json"
    old = json.loads(meta_path.read_text()) if meta_path.exists() else None
    resume_from = None
    if resume and old and {k: old.get(k) for k in meta} == meta and Path(cfg["paths"]["db"]).exists():
        db = sqlite3.connect(cfg["paths"]["db"])
        row = db.execute("SELECT MAX(ts) FROM cycles").fetchone()
        db.close()
        if row and row[0]:
            resume_from = pd.Timestamp(row[0]).to_pydatetime() + timedelta(minutes=cfg["scheduler"]["interval_minutes"])
    if resume_from is None:
        for key in ("db", "jsonl", "kill_switch"):
            p = Path(cfg["paths"][key])
            if p.exists():
                p.unlink()
        if resume and old:
            print("Reprise impossible (code, configuration ou données différents) : rejeu complet depuis le début.")
        meta["started_at"] = datetime.now(timezone.utc).isoformat()
        meta_path.write_text(json.dumps(meta, indent=2))
    else:
        print(f"REPRISE après interruption à partir de {resume_from:%Y-%m-%d %H:%M} UTC (état du compte conservé).")
        start = resume_from
    print(f"Données : {first} → {last}. Cycles simulés du {start:%Y-%m-%d %H:%M} au {last:%Y-%m-%d %H:%M} UTC "
          f"({warmup_days} jours réservés au préchauffage des indicateurs).", flush=True)
    n = replay(cfg, start, last, provider=prov, keep_records=False, progress=progress,
               stop_at=stop_at) if start <= last else 0
    db = sqlite3.connect(cfg["paths"]["db"])
    last_ts = db.execute("SELECT MAX(ts) FROM cycles").fetchone()[0]
    db.close()
    import time as _t
    finished = not (stop_at is not None and _t.time() > stop_at)     # arrêté par le budget = pas fini
    if state is not None:
        state["finished"] = finished
        state["last_cycle"] = last_ts
    title = f"Rejeu V2 sur données Dukascopy M1 ({', '.join(cfg['symbols'])})"
    if not finished:
        title = f"RAPPORT PARTIEL (rejeu arrêté au {last_ts}, reprise automatique) — " + title
    text, trades = build_report(cfg["paths"]["db"], title)
    (bt_dir / "report.md").write_text(text, encoding="utf-8")
    cols = [c for c in (trades.columns if not trades.empty else []) if c != "setup_json"]
    (trades[cols] if not trades.empty else pd.DataFrame(columns=["aucun_trade"])).to_csv(bt_dir / "trades.csv", index=False)
    try:                                   # META-SKILL : audit du journal (observations, jamais des règles)
        from .meta import journal_audit
        journal_audit.run(cfg["paths"]["db"], bt_dir, provider=prov)
    except Exception as e:                 # pragma: no cover
        print(f"audit du journal non produit : {e}")
    meta = json.loads(meta_path.read_text())
    meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"\n{n:,} cycles rejoués dans cette exécution.\n")
    print(text)
    print(f"\nRapport : {bt_dir / 'report.md'}  |  Trades : {bt_dir / 'trades.csv'}  |  Journal : {bt_dir / 'journal.sqlite'}")
    return text


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
            st.flush()

    def flush(self):
        for st in self.streams:
            st.flush()


def run_pipeline(cfg: dict, start: date | None = None, end: date | None = None,
                 results_dir: Path | None = None, data_root: Path | None = None,
                 fetcher=None, retry_wait: int = 30, progress: bool = True,
                 time_budget_min: float | None = None) -> int:
    """UNE commande : téléchargement Dukascopy (reprenable) → validation → backtest (reprenable)
    → results/ (report.md, trades.csv, quality_report.json, pipeline.log, STATUS.txt).

    time_budget_min : durée max de ce lancement. S'il reste du travail, STATUS.txt vaut « EN COURS »
    et le lancement suivant reprend exactement là où celui-ci s'est arrêté."""
    import shutil
    import sys
    import time
    import traceback
    from .data import dukascopy
    from .data.providers import CSVProvider
    t_start = time.time()
    stop_at = t_start + time_budget_min * 60 if time_budget_min else None
    results = Path(results_dir) if results_dir else ROOT / "results"
    results.mkdir(parents=True, exist_ok=True)
    log_f = open(results / "pipeline.log", "a", encoding="utf-8")
    out, err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _Tee(out, log_f), _Tee(err, log_f)
    status, step, detail = "ÉCHEC", "démarrage", ""
    try:
        if start is None or end is None:
            start, end = default_period()
        print(f"=== Pipeline démarré {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC — période {start} → {end}"
              + (f" — budget {time_budget_min:.0f} min" if time_budget_min else "") + " ===")
        print("Mode PAPER uniquement. Aucun broker, aucun argent réel. Stratégies et paramètres inchangés.")
        data_root_ = Path(data_root) if data_root else ROOT / "data"
        csv_dir, raw = _csv_dir(cfg), data_root_ / "dukascopy_raw"
        step = "téléchargement Dukascopy"
        # le téléchargement s'arrête 45 min avant la fin du budget pour laisser du temps au backtest
        dl_deadline = stop_at - 45 * 60 if stop_at else None
        attempt = 0
        while True:
            attempt += 1
            print(f"--- Étape 1/3 : {step} (passage {attempt}) ---")
            rep = dukascopy.prepare(cfg["symbols"], start, end, raw, csv_dir, fetcher=fetcher or dukascopy.fetch,
                                    deadline=dl_deadline)
            if not rep.get("incomplete"):
                break
            dl = rep["download"]
            remaining = len(dl["errors"]) + dl["postponed"]
            if dl_deadline and time.time() > dl_deadline:
                status, detail = "EN COURS", f"téléchargement : {remaining} fichiers restants"
                print(f"Budget de temps atteint : {remaining} fichiers restants, reprise au prochain lancement.")
                return 0
            if not dl_deadline and attempt >= 5:
                raise RuntimeError(f"téléchargement incomplet après {attempt} passages : {dl['errors'][:5]}")
            print(f"{remaining} fichiers encore refusés par Dukascopy, nouveau passage dans {retry_wait} s…")
            time.sleep(retry_wait)
        step = "validation"
        print(f"--- Étape 2/3 : {step} ---")
        missing = [s for s, q in rep["symbols"].items() if "error" in q]
        if missing:
            raise RuntimeError(f"aucune donnée pour {missing}")
        prov = CSVProvider(cfg["symbols"], csv_dir)
        first, last = prov.time_range()
        print(f"Validation OK : {', '.join(cfg['symbols'])}, période commune {first} → {last}")
        step = "backtest"
        print(f"--- Étape 3/3 : {step} (V2 inchangée) ---")
        state: dict = {}
        run_backtest(cfg, resume=True, out_dir=data_root_ / "backtest", progress=progress,
                     stop_at=(stop_at - 5 * 60) if stop_at else None, state=state)
        if state.get("finished", True):
            status = "OK"
        else:
            status, detail = "EN COURS", f"backtest arrêté au cycle {state.get('last_cycle')}, reprise au prochain lancement"
        return 0
    except Exception as e:
        print(f"ERREUR pendant l'étape « {step} » : {e}")
        traceback.print_exc()
        return 1
    finally:
        bt = (Path(data_root) if data_root else ROOT / "data") / "backtest"
        for src in (bt / "report.md", bt / "trades.csv", bt / "run_meta.json", bt / "journal_audit.md",
                    bt / "journal_audit.json", _csv_dir(cfg) / "quality_report.json"):
            if src.exists():
                shutil.copy2(src, results / src.name)
        (results / "STATUS.txt").write_text(
            f"{status}\nétape : {step}\n" + (f"détail : {detail}\n" if detail else "")
            + f"fin : {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n", encoding="utf-8")
        print(f"=== Pipeline terminé : {status} (étape {step}{', ' + detail if detail else ''}) — fichiers dans {results} ===")
        sys.stdout, sys.stderr = out, err
        log_f.close()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="forex_agent")
    ap.add_argument("--config", default=None)
    ap.add_argument("--allow-synthetic", action="store_true", help="autoriser run-once/loop sur marché simulé (démo)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run-once")
    lp = sub.add_parser("loop")
    lp.add_argument("--max-cycles", type=int, default=None)
    rp = sub.add_parser("replay")
    rp.add_argument("--start", default=None, help="UTC, ex. 2026-09-07T00:00")
    rp.add_argument("--days", type=float, default=5)
    rp.add_argument("--fresh", action="store_true", help="repartir d'un journal vide")
    rp.add_argument("--quiet", action="store_true")
    sub.add_parser("report")
    sub.add_parser("reset")
    dp = sub.add_parser("data-download", help="télécharge Dukascopy M1 BID+ASK et prépare les CSV")
    dp.add_argument("--symbols", nargs="+", default=None)
    dp.add_argument("--start", default=None, help="AAAA-MM-JJ (défaut : début des 6 derniers mois complets)")
    dp.add_argument("--end", default=None, help="AAAA-MM-JJ inclus (défaut : fin du dernier mois complet)")
    dp.add_argument("--workers", type=int, default=3)
    dp.add_argument("--time-budget-min", type=float, default=None,
                    help="au-delà, les fichiers restants sont laissés pour le lancement suivant")
    sub.add_parser("data-validate", help="relit et valide les CSV M1 comme le fera le rejeu")
    bp = sub.add_parser("backtest", help="rejoue la V2 sur TOUTE la période CSV, journal séparé, puis rapport")
    bp.add_argument("--warmup-days", type=int, default=7, help="historique réservé au calcul des indicateurs")
    bp.add_argument("--resume", action="store_true", help="reprendre un backtest interrompu (à l'identique)")
    ja = sub.add_parser("journal-audit", help="audit chiffré du journal (observations → hypothèses, jamais des règles)")
    ja.add_argument("--db", default=None, help="base du journal (défaut : journal paper)")
    ja.add_argument("--out", default=None, help="dossier de sortie (défaut : data/audit)")
    pp = sub.add_parser("pipeline", help="téléchargement + validation + backtest + résultats, en une commande")
    pp.add_argument("--start", default=None)
    pp.add_argument("--end", default=None)
    pp.add_argument("--time-budget-min", type=float, default=None, help="durée max de ce lancement (reprise ensuite)")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if a.cmd in ("reset",) or (a.cmd == "replay" and a.fresh):
        for key in ("db", "jsonl", "kill_switch"):
            p = resolve_path(cfg, key)
            if p.exists():
                p.unlink()
        if a.cmd == "reset":
            print("Journal paper effacé : prochain cycle à", cfg["account"]["starting_capital"], cfg["account"]["currency"])
            return
    if a.cmd in ("run-once", "loop") and cfg["data"]["provider"] == "synthetic" and not a.allow_synthetic:
        print("Le scheduler temps réel a besoin de VRAIS prix : data.provider vaut « synthetic » (marché simulé).\n"
              "Utiliser FOREX_DATA_PROVIDER=oanda (compte démo, lecture seule), ou --allow-synthetic pour une démo.")
        raise SystemExit(2)
    if a.cmd == "run-once":
        rec = run_once(cfg)
        print(f"{rec['ts']} capital {rec['equity']:.2f} | {rec['summary']}")
    elif a.cmd == "loop":
        loop(cfg, a.max_cycles)
    elif a.cmd == "replay":
        if a.start:
            start = pd.Timestamp(a.start, tz="UTC").to_pydatetime()
        else:  # premier lundi après 4 jours d'historique (préchauffage des indicateurs H1)
            s0 = pd.Timestamp(cfg["data"]["synthetic"]["start"], tz="UTC") + pd.Timedelta(days=4)
            start = (s0 + pd.Timedelta(days=(7 - s0.weekday()) % 7)).to_pydatetime()
        end = start + timedelta(days=a.days)
        recs = replay(cfg, start, end, verbose=not a.quiet)
        print(f"\n{len(recs)} cycles rejoués du {start:%Y-%m-%d %H:%M} au {end:%Y-%m-%d %H:%M} UTC\n")
        print(report(cfg))
    elif a.cmd == "report":
        print(report(cfg))
    elif a.cmd == "data-download":
        from .data import dukascopy
        start, end = default_period() if not (a.start and a.end) else (None, None)
        start = date.fromisoformat(a.start) if a.start else start
        end = date.fromisoformat(a.end) if a.end else end
        csv_dir = _csv_dir(cfg)
        import time as _time
        deadline = _time.time() + a.time_budget_min * 60 if a.time_budget_min else None
        rep = dukascopy.prepare(a.symbols or cfg["symbols"], start, end, ROOT / "data" / "dukascopy_raw", csv_dir,
                                workers=a.workers, deadline=deadline)
        complete = not rep.get("incomplete")
        (ROOT / "data").mkdir(exist_ok=True)
        (ROOT / "data" / "download_status.txt").write_text(
            ("COMPLETE" if complete else "INCOMPLETE") + f"\n{start} {end}\n", encoding="utf-8")
        dl = rep["download"]
        print(f"Téléchargement {'COMPLET' if complete else 'INCOMPLET'} : {dl['downloaded']} téléchargés, "
              f"{dl['cached']} en cache, {len(dl['errors'])} erreurs, {dl['postponed']} reportés")
        errs = dl["errors"]
        print(f"\nRapport qualité : {csv_dir / 'quality_report.json'}")
        if errs:
            print(f"ATTENTION : {len(errs)} fichiers en erreur (relancer la même commande reprend là où ça s'est arrêté) :")
            for e in errs[:10]:
                print("  ", e)
    elif a.cmd == "data-validate":
        from .data.providers import CSVProvider
        prov = CSVProvider(cfg["symbols"], _csv_dir(cfg))
        first, last = prov.time_range()
        for sym in cfg["symbols"]:
            n = len(prov.m1(sym, first, last + timedelta(minutes=1)))
            print(f"{sym} : {n:,} minutes M1 valides")
        print(f"Période commune : {first} → {last}")
    elif a.cmd == "backtest":
        run_backtest(cfg, a.warmup_days, resume=a.resume)
    elif a.cmd == "journal-audit":
        from .meta import journal_audit
        db = Path(a.db) if a.db else resolve_path(cfg, "db")
        out = Path(a.out) if a.out else ROOT / "data" / "audit"
        print(f"Audit écrit : {journal_audit.run(db, out)}")
    elif a.cmd == "pipeline":
        raise SystemExit(run_pipeline(cfg, date.fromisoformat(a.start) if a.start else None,
                                      date.fromisoformat(a.end) if a.end else None,
                                      time_budget_min=a.time_budget_min))


if __name__ == "__main__":
    main()
