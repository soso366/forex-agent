"""Classement des 30 comptes à partir des chiffres publiés (accounts.json).

Règles fixées à l'avance, appliquées mécaniquement. Une valeur non publiée ne rapporte aucun point.
Usage : python rank.py  → classement.csv et classement.md
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
EXCLUDE_WORDS = ("martingale", "grille", "moyenne à la baisse", "renfort")


def worst_dd(a):
    vals = [v for v in (a["dd_bal_max"], a["dd_eq_rel"]) if v is not None]
    return max(vals) if vals else None


def evaluate(a):
    excl = [f for f in a["risk_flags"] if any(w in f for w in EXCLUDE_WORDS)]
    dd = worst_dd(a)
    real = bool(a["server"]) and any(k in a["server"].lower() for k in ("live", "real"))
    conc = None
    if a["best"] and a["avg_win"]:
        conc = round(a["best"] / a["avg_win"], 1)
    checks = {
        "reel_indique_par_serveur": real,
        "historique_12m": (a["weeks"] or 0) >= 52,
        "pf_1_30": (a["pf"] or 0) >= 1.30,
        "dd_moins_15": dd is not None and dd < 15,
        "trades_300": (a["trades"] or 0) >= 300,
        "trader_eurusd_50": (a["eur_share"] or 0) >= 50,
        "pas_martingale_grille": not excl,
    }
    pts = 0.0
    pts += 2 if (a["weeks"] or 0) >= 104 else 1 if (a["weeks"] or 0) >= 52 else 0
    pts += 2 if (a["pf"] or 0) >= 2 else 1 if (a["pf"] or 0) >= 1.3 else 0
    pts += 0 if dd is None else 2 if dd < 15 else 1 if dd < 25 else 0
    pts += 2 if (a["trades"] or 0) >= 500 else 1 if (a["trades"] or 0) >= 300 else 0
    e = a["eur_share"] or 0
    pts += 2 if e >= 90 else 1 if e >= 40 else 0.5 if e >= 20 else 0
    pts += 1 if conc is not None and conc <= 50 else 0
    pts += 1 if real else 0
    passed = sum(checks.values())
    return {
        "id": a["id"], "nom": a["name"], "lien": f"https://www.mql5.com/en/signals/{a['id']}",
        "serveur": a["server"] or "non publié", "semaines": a["weeks"], "pf": a["pf"],
        "dd_pire_%": dd, "transactions": a["trades"], "reussite_%": a["win"],
        "gain_moy": a["avg_win"], "perte_moy": a["avg_loss"],
        "ratio_gain_perte": round(abs(a["avg_win"] / a["avg_loss"]), 2) if a["avg_win"] and a["avg_loss"] else None,
        "meilleur_trade_x_gain_moy": conc, "duree_moy": a["hold"], "part_eurusd_%": a["eur_share"],
        "paires": a["pairs"], "criteres_ok": f"{passed}/7", "score": pts,
        "exclu": "; ".join(excl) or "", "echecs": ", ".join(k for k, v in checks.items() if not v),
    }


def main():
    accounts = json.loads((HERE / "accounts.json").read_text())["accounts"]
    rows = [evaluate(a) for a in accounts]
    rows.sort(key=lambda r: (r["exclu"] != "", -r["score"], -(r["pf"] or 0)))
    for i, r in enumerate(rows, 1):
        r["rang"] = i
    cols = ["rang"] + [c for c in rows[0] if c != "rang"]
    with open(HERE / "classement.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    lines = ["| Rang | Compte | Sem. | PF | DD pire % | Trades | EUR/USD % | Critères | Score | Exclusion / échecs |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['rang']} | [{r['nom']}]({r['lien']}) | {r['semaines'] or '?'} | {r['pf'] or '?'} | "
                     f"{r['dd_pire_%'] if r['dd_pire_%'] is not None else '?'} | {r['transactions']} | {r['part_eurusd_%']} | "
                     f"{r['criteres_ok']} | {r['score']:g} | {('EXCLU : ' + r['exclu']) if r['exclu'] else r['echecs']} |")
    (HERE / "classement.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    full = [r for r in rows if r["criteres_ok"] == "7/7"]
    print(f"\nComptes qui remplissent les 7 critères : {len(full)}")


if __name__ == "__main__":
    main()
