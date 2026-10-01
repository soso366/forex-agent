"""META-SKILL 3 — Audit périodique du journal des trades, sans mémoire subjective.

Chiffres uniquement, calculés depuis la base du journal. Chaque constat est une OBSERVATION :
elle ne devient JAMAIS une règle automatiquement. Chaîne obligatoire :
observation → hypothèse → backtest → validation → OOS → éventuellement intégration.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

MIN_N = 30          # en dessous : « échantillon insuffisant », rien à conclure
CTX_MIN_N = 8       # taille minimale d'un contexte pour être signalé


def load(db_path: str | Path) -> pd.DataFrame:
    con = sqlite3.connect(str(db_path))
    try:
        t = pd.read_sql_query("SELECT * FROM trades WHERE status = 'closed'", con)
    finally:
        con.close()
    return prepare(t)


def prepare(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    if t.empty:
        return t
    t["entry_dt"] = pd.to_datetime(t["entry_time"], utc=True)
    t["exit_dt"] = pd.to_datetime(t["exit_time"], utc=True)
    t["r"] = t["r_multiple"].astype(float)
    t["win"] = t["r"] > 0
    t["hour"] = t["entry_dt"].dt.hour
    t["weekday"] = t["entry_dt"].dt.day_name()
    t["exit_kind"] = t["exit_reason"].fillna("").str.split(" ").str[0].str.rstrip(":")
    return t


def summary(r: pd.Series) -> dict:
    r = r.astype(float)
    n = len(r)
    if n == 0:
        return {"n": 0}
    w, l = r[r > 0], r[r <= 0]
    sd = r.std(ddof=1) if n > 1 else np.nan
    return {"n": n, "win_rate": round(float((r > 0).mean()), 3), "exp_r": round(float(r.mean()), 3),
            "avg_win_r": round(float(w.mean()), 3) if len(w) else None,
            "avg_loss_r": round(float(l.mean()), 3) if len(l) else None,
            "pf": round(float(w.sum() / -l.sum()), 2) if l.sum() < 0 else None,
            "total_r": round(float(r.sum()), 2),
            "t": round(float(r.mean() / (sd / np.sqrt(n))), 2) if n > 1 and sd > 0 else None,
            "enough": n >= MIN_N}


def table(t: pd.DataFrame, col) -> dict:
    return {str(k): summary(g["r"]) for k, g in t.groupby(col, observed=True)}


def losing_streak(r: pd.Series) -> int:
    best = cur = 0
    for x in r:
        cur = cur + 1 if x <= 0 else 0
        best = max(best, cur)
    return best


def early_exits(t: pd.DataFrame, provider=None, hold_min: int = 30) -> dict:
    """Sorties de gestion (ni stop, ni cible, ni temps) : le prix a-t-il ensuite continué en faveur ?
    Avec données de prix : mouvement favorable maximal entre la sortie et la fin des 30 min. Sinon : MFE vs résultat."""
    mg = t[~t["exit_kind"].isin(["STOP_LOSS", "STOP", "TIME_STOP", "TARGET"])].copy()
    out = {"n_management_exits": int(len(mg))}
    if mg.empty:
        return out
    if provider is not None:
        gains = []
        for _, x in mg.iterrows():
            try:
                end = x["entry_dt"] + timedelta(minutes=hold_min)
                m1 = provider.m1(x["symbol"], x["exit_dt"].to_pydatetime(), end.to_pydatetime())
                risk = abs(x["entry"] - x["initial_stop"])
                d = 1 if x["direction"] == "BUY" else -1
                best = (m1["h"].max() - x["exit_price"]) if d == 1 else (x["exit_price"] - m1["al"].min())
                gains.append(best / risk if risk else np.nan)
            except Exception:
                gains.append(np.nan)
        mg["post_exit_mfe_r"] = gains
        g = mg["post_exit_mfe_r"].dropna()
        out.update({"method": "prix après sortie", "measured": int(len(g)),
                    "share_continued_0_5R": round(float((g >= 0.5).mean()), 3) if len(g) else None,
                    "median_post_exit_mfe_r": round(float(g.median()), 3) if len(g) else None})
    else:
        gap = mg["mfe_r"] - mg["r"]
        out.update({"method": "MFE pendant le trade (sans prix après sortie)",
                    "share_gave_back_0_5R": round(float((gap >= 0.5).mean()), 3),
                    "median_gave_back_r": round(float(gap.median()), 3)})
    return out


def hidden_correlations(t: pd.DataFrame) -> dict:
    """Trades ouverts en même temps sur des paires différentes : leurs résultats sont-ils liés ?"""
    rows = []
    s = t.sort_values("entry_dt").reset_index(drop=True)
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            if s.at[j, "entry_dt"] >= s.at[i, "exit_dt"]:
                break
            if s.at[i, "symbol"] != s.at[j, "symbol"]:
                rows.append((s.at[i, "r"], s.at[j, "r"], s.at[i, "symbol"], s.at[j, "symbol"]))
    out = {"overlapping_pairs": len(rows)}
    if len(rows) >= 10:
        a = np.array([[x[0], x[1]] for x in rows])
        out["corr_r"] = round(float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]), 2)
        out["same_sign_share"] = round(float((np.sign(a[:, 0]) == np.sign(a[:, 1])).mean()), 2)
    day = t.groupby(t["entry_dt"].dt.date)["r"].agg(["size", "sum", lambda r: (r > 0).all() or (r <= 0).all()])
    multi = day[day["size"] >= 2]
    if len(multi):
        out["days_with_2plus_trades"] = int(len(multi))
        out["share_days_all_same_outcome"] = round(float(multi.iloc[:, 2].mean()), 2)
    return out


def observations(t: pd.DataFrame, res: dict) -> list[dict]:
    """Constats chiffrés → hypothèses à TESTER. Jamais des règles."""
    obs = []

    def add(kind, text, n):
        status = "échantillon insuffisant : ne rien conclure" if n < MIN_N else "hypothèse à tester (backtest → validation → OOS)"
        obs.append({"type": kind, "constat": text, "n": int(n), "statut": status})

    for name, s in res["by_strategy"].items():
        if s["n"] >= CTX_MIN_N and s["exp_r"] < 0:
            add("stratégie", f"{name} : {s['exp_r']:+.2f} R/trade sur {s['n']} trades (PF {s['pf']})", s["n"])
    for dims in (["strategy", "regime"], ["strategy", "session"], ["symbol", "hour"], ["strategy", "symbol"]):
        g = t.groupby(dims, observed=True)["r"].agg(["size", "mean"])
        for k, row in g[(g["size"] >= CTX_MIN_N) & (g["mean"] <= -0.3)].iterrows():
            k = k if isinstance(k, tuple) else (k,)
            add("contexte perdant", f"{' × '.join(map(str, k))} : {row['mean']:+.2f} R/trade sur {int(row['size'])} trades",
                row["size"])
    wl = res["winners_turned_losers"]
    if wl["n"] >= CTX_MIN_N and wl["share"] >= 0.25:
        add("gestion", f"{wl['share']:.0%} des perdants avaient d'abord atteint +0,5 R (MFE)", wl["n"])
    ee = res["early_exits"]
    if ee.get("share_continued_0_5R") and ee["share_continued_0_5R"] >= 0.4:
        add("gestion", f"{ee['share_continued_0_5R']:.0%} des sorties de gestion ont été suivies d'un mouvement "
                       f"favorable ≥ 0,5 R avant la fin des 30 min", ee.get("measured", 0))
    hc = res["hidden_correlations"]
    if hc.get("corr_r") is not None and hc["corr_r"] >= 0.3:
        add("corrélation", f"trades simultanés sur paires différentes : corrélation des R = {hc['corr_r']}",
            hc["overlapping_pairs"])
    for strat, k in res["losing_streaks"].items():
        if k >= 5:
            add("série", f"{strat} : série de {k} pertes consécutives", res["by_strategy"][strat]["n"])
    return obs


def audit(t: pd.DataFrame, provider=None) -> dict:
    t = prepare(t) if "r" not in t.columns else t
    if t.empty:
        return {"n": 0, "message": "journal vide : rien à auditer"}
    w, l = t[t["win"]], t[~t["win"]]
    res = {
        "period": [str(t["entry_dt"].min()), str(t["entry_dt"].max())],
        "global": summary(t["r"]),
        "by_strategy": table(t, "strategy"),
        "by_pair": table(t, "symbol"),
        "by_hour_utc": table(t, "hour"),
        "by_session": table(t, "session") if "session" in t else {},
        "by_weekday": table(t, "weekday"),
        "by_exit": table(t, "exit_kind"),
        "duration_min": {"winners_median": float(w["duration_min"].median()) if len(w) else None,
                         "losers_median": float(l["duration_min"].median()) if len(l) else None},
        "mfe_mae": {"winners": {"mfe": round(float(w["mfe_r"].median()), 2) if len(w) else None,
                                "mae": round(float(w["mae_r"].median()), 2) if len(w) else None},
                    "losers": {"mfe": round(float(l["mfe_r"].median()), 2) if len(l) else None,
                               "mae": round(float(l["mae_r"].median()), 2) if len(l) else None}},
        "winners_turned_losers": {"n": int(((t["mfe_r"] >= 0.5) & (t["r"] <= 0)).sum()),
                                  "share": round(float(((t["mfe_r"] >= 0.5) & (t["r"] <= 0)).sum() / max(len(l), 1)), 3)},
        "early_exits": early_exits(t, provider),
        "losing_streaks": {s: losing_streak(g.sort_values("entry_dt")["r"]) for s, g in t.groupby("strategy")},
        "hidden_correlations": hidden_correlations(t),
    }
    res["observations"] = observations(t, res)
    res["rule"] = ("Une observation du journal ne devient JAMAIS une règle automatiquement : "
                   "observation → hypothèse → backtest → validation → OOS → éventuellement intégration.")
    return res


def to_markdown(res: dict) -> str:
    if not res.get("global"):
        return "# Audit du journal\n\nJournal vide.\n"
    L = ["# Audit du journal des trades", "", f"Période : {res['period'][0][:16]} → {res['period'][1][:16]}", "",
         f"> {res['rule']}", ""]

    def tab(title, d):
        L.extend([f"## {title}", "", "| | n | win | esp. R | gain moy. | perte moy. | PF | total R |",
                  "|---|---|---|---|---|---|---|---|"])
        for k, s in d.items():
            flag = "" if s.get("enough") else " ⚠"
            L.append(f"| {k}{flag} | {s['n']} | {s['win_rate']:.0%} | {s['exp_r']:+.3f} | {s['avg_win_r'] or '—'} | "
                     f"{s['avg_loss_r'] or '—'} | {s['pf'] or '—'} | {s['total_r']:+.2f} |")
        L.append("")
    tab("Global", {"tous": res["global"]})
    tab("Par stratégie", res["by_strategy"])
    tab("Par paire", res["by_pair"])
    tab("Par séance", res["by_session"])
    tab("Par heure (UTC)", res["by_hour_utc"])
    tab("Par jour de semaine", res["by_weekday"])
    tab("Par type de sortie", res["by_exit"])
    L += ["## Durée, MFE / MAE", "",
          f"- Durée médiane : gagnants {res['duration_min']['winners_median']} min, perdants {res['duration_min']['losers_median']} min",
          f"- MFE / MAE médians (R) : gagnants {res['mfe_mae']['winners']}, perdants {res['mfe_mae']['losers']}",
          f"- Gagnants devenus perdants (MFE ≥ +0,5 R puis perte) : {res['winners_turned_losers']['n']} "
          f"({res['winners_turned_losers']['share']:.0%} des perdants)",
          f"- Sorties de gestion : {json.dumps(res['early_exits'], ensure_ascii=False)}",
          f"- Séries de pertes max : {json.dumps(res['losing_streaks'], ensure_ascii=False)}",
          f"- Corrélations cachées : {json.dumps(res['hidden_correlations'], ensure_ascii=False)}", "",
          "## Observations (hypothèses à tester, pas des règles)", ""]
    if not res["observations"]:
        L.append("Aucune observation au-dessus des seuils.")
    for o in res["observations"]:
        L.append(f"- **{o['type']}** — {o['constat']} · n = {o['n']} · *{o['statut']}*")
    L += ["", "⚠ = moins de 30 trades : ne rien conclure."]
    return "\n".join(L) + "\n"


def run(db_path, out_dir, provider=None) -> Path:
    res = audit(load(db_path), provider)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "journal_audit.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    p = out / "journal_audit.md"
    p.write_text(to_markdown(res), encoding="utf-8")
    return p
