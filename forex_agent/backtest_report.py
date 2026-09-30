"""Rapport de rejeu : mesure honnête de la V2 telle qu'elle est.

Tout vient du journal SQLite (cycles, snapshots par paire, trades) : rien n'est recalculé
à partir des stratégies, rien n'est filtré après coup.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


def _norm(reason: str) -> str:
    """Regroupe les raisons de refus (les nombres varient d'un cycle à l'autre)."""
    r = re.sub(r"[-+]?\d+([.,]\d+)?", "#", reason or "")
    r = re.sub(r"\(jusqu'à [^)]*\)", "", r)
    return r.strip()[:110]


def _breakdown(df: pd.DataFrame, col: str) -> list[str]:
    out = []
    for key, g in df.groupby(df[col].fillna("—").astype(str)):
        wins = (g.pnl_eur > 0).sum()
        out.append(f"| {key} | {len(g)} | {wins} / {len(g) - wins} | {wins / len(g) * 100:.0f} % | "
                   f"{g.pnl_eur.sum():+.2f} | {g.r_multiple.sum():+.2f} | {g.r_multiple.mean():+.3f} |")
    return out


def build_report(db_path: str | Path, title: str = "Rejeu V2") -> tuple[str, pd.DataFrame]:
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    acc = db.execute("SELECT * FROM account WHERE id=1").fetchone()
    if acc is None:
        return "Journal vide.", pd.DataFrame()
    cycles = db.execute("SELECT COUNT(*), MIN(ts), MAX(ts), SUM(error IS NOT NULL) FROM cycles").fetchone()
    trades = pd.DataFrame([dict(r) for r in db.execute("SELECT * FROM trades WHERE status='closed' ORDER BY exit_time")])
    still_open = db.execute("SELECT COUNT(*) FROM trades WHERE status='open'").fetchone()[0]

    # ---------- entonnoir par stratégie (snapshots paire × cycle)
    detections, refused_ess, missing, qualified, after_q = Counter(), Counter(), defaultdict(Counter), Counter(), defaultdict(Counter)
    decisions, regimes = Counter(), Counter()
    for row in db.execute("SELECT decision, chosen_strategy, reason, regime, opportunities FROM market_snapshots"):
        decisions[row["decision"]] += 1
        if row["regime"]:
            regimes[row["regime"]] += 1
        for o in json.loads(row["opportunities"] or "[]"):
            s = o["strategy"]
            detections[s] += 1
            miss = [k for k in o.get("essential", []) if not o["confirmations"].get(k)]
            if miss:
                refused_ess[s] += 1
                for k in miss:
                    missing[s][k] += 1
                continue
            qualified[s] += 1
            if row["decision"] in ("BUY", "SELL") and row["chosen_strategy"] == s and row["decision"] == o["direction"]:
                continue                                        # exécuté (compté via la table trades)
            if row["decision"] in ("BUY", "SELL"):
                after_q[s][f"autre setup exécuté sur la paire ({row['chosen_strategy']})"] += 1
            elif row["decision"] in ("HOLD", "MOVE_STOP", "CLOSE", "TAKE_PROFIT"):
                after_q[s]["position déjà ouverte ou gérée sur la paire"] += 1
            else:
                after_q[s][_norm(row["reason"])] += 1

    L = [f"# {title}", ""]
    L += [f"Période des cycles : {cycles[1]} → {cycles[2]}", ""]
    L += ["## Vue d'ensemble", "",
          f"- Cycles : **{cycles[0]:,}** (erreurs : {cycles[3] or 0})",
          f"- Décisions paire × cycle : " + ", ".join(f"{k} {v:,}" for k, v in decisions.most_common()),
          f"- NO TRADE : **{decisions.get('NO_TRADE', 0):,}** sur {sum(decisions.values()):,} décisions",
          f"- Régimes observés : " + ", ".join(f"{k} {v:,}" for k, v in regimes.most_common()),
          f"- Capital : {acc['starting_capital']:.2f} → {acc['balance']:.2f} {acc['currency']} "
          f"({(acc['balance'] / acc['starting_capital'] - 1) * 100:+.2f} %), plus haut {acc['peak_equity']:.2f}",
          f"- Positions encore ouvertes à la fin : {still_open}", ""]

    if trades.empty:
        L.append("**Aucun trade exécuté.**")
    else:
        t = trades
        wins, losses = t[t.pnl_eur > 0], t[t.pnl_eur <= 0]
        gp, gl = wins.pnl_eur.sum(), -losses.pnl_eur.sum()
        eq = pd.concat([pd.Series([acc["starting_capital"]]), t["balance_after"]], ignore_index=True)
        dd_eur = (eq.cummax() - eq).max()
        dd_pct = ((eq.cummax() - eq) / eq.cummax()).max() * 100
        r_cum = t.r_multiple.cumsum()
        dd_r = (r_cum.cummax().clip(lower=0) - r_cum).max()
        time_exits = t.exit_reason.str.startswith("TIME_STOP").sum()
        exits = Counter(re.split(r"[ :(]", r)[0] for r in t.exit_reason)
        L += ["## Résultats", "",
              "| Mesure | Valeur |", "|---|---|",
              f"| Trades | {len(t)} |",
              f"| Gagnants / perdants | {len(wins)} / {len(losses)} |",
              f"| Win rate | {len(wins) / len(t) * 100:.1f} % |",
              f"| PnL | {t.pnl_eur.sum():+.2f} {acc['currency']} |",
              f"| PnL en R | {t.r_multiple.sum():+.2f} R |",
              f"| Expectancy | {t.r_multiple.mean():+.3f} R / trade |",
              f"| Profit factor | {gp / gl if gl else float('inf'):.2f} |",
              f"| Drawdown max | {dd_pct:.2f} % ({dd_eur:.2f} {acc['currency']}, {dd_r:.2f} R) |",
              f"| MFE moyen / médian | {t.mfe_r.mean():.2f} R / {t.mfe_r.median():.2f} R |",
              f"| MAE moyen / médian | {t.mae_r.mean():.2f} R / {t.mae_r.median():.2f} R |",
              f"| Durée moyenne | {t.duration_min.mean():.1f} min |",
              f"| Sorties par limite 30 min | {time_exits} ({time_exits / len(t) * 100:.0f} %) |",
              f"| Cas SL/TP ambigus (stop d'abord) | {int(t.intrabar_ambiguous.sum())} |", "",
              "Raisons de sortie : " + ", ".join(f"{k} {v}" for k, v in exits.most_common()), ""]
        head = ["| Groupe | Trades | Gagnants / perdants | Win rate | PnL | PnL R | Expectancy R |",
                "|---|---|---|---|---|---|---|"]
        for label, col in (("Par stratégie", "strategy"), ("Par paire", "symbol"),
                           ("Par régime à l'entrée", "regime"), ("Par session", "session"),
                           ("Par killzone", "killzone")):
            L += [f"### {label}", ""] + head + _breakdown(t, col) + [""]

    L += ["## Entonnoir par stratégie", "",
          "Détections = occurrences paire × cycle où le motif existe ; un même motif présent sur plusieurs "
          "cycles consécutifs est compté à chaque cycle.", ""]
    names = sorted(set(detections) | (set(trades.strategy) if not trades.empty else set()))
    L += ["| Stratégie | Détections | Refusées (conditions) | Qualifiées | Qualifiées non exécutées | Exécutées | Gagnants / perdants |",
          "|---|---|---|---|---|---|---|"]
    for s in names:
        ex = trades[trades.strategy == s] if not trades.empty else pd.DataFrame()
        w = int((ex.pnl_eur > 0).sum()) if len(ex) else 0
        L.append(f"| {s} | {detections[s]:,} | {refused_ess[s]:,} | {qualified[s]:,} | "
                 f"{sum(after_q[s].values()):,} | {len(ex)} | {w} / {len(ex) - w} |")
    L.append("")
    for s in names:
        L += [f"### {s}", "", "Conditions essentielles manquantes (une détection peut en manquer plusieurs) :"]
        L += [f"- {k} : {v:,}" for k, v in missing[s].most_common()] or ["- aucune"]
        L += ["", "Qualifiées mais non exécutées, raison :"]
        L += [f"- {k} : {v:,}" for k, v in after_q[s].most_common(8)] or ["- aucune"]
        L.append("")
    n = len(trades)
    L += ["## Lecture", "",
          "Échantillon < 100 trades : aucune conclusion statistique possible." if n < 100 else
          f"{n} trades : échantillon exploitable, à confirmer hors échantillon avant toute décision.",
          "Aucun paramètre, aucune cible, aucune durée ni aucun risque n'ont été modifiés pour ce rejeu."]
    db.close()
    return "\n".join(L), trades
