"""Construit le catalogue unique des comptes consultés (toutes plateformes) → catalogue_comptes.csv / .md

Priorité de l'information quand un compte apparaît plusieurs fois : A (historique) > B (page) > C (liste).
"""
import csv
import json
from pathlib import Path

from catalog_data import COLLECTIVE2, CTRADER, MQL5_LIST, MYFXBOOK

ROOT = Path(__file__).resolve().parent.parent
GRID_WORDS = ("martingale", "grille", "moyenne à la baisse", "renfort")


def main():
    rows = {}
    # B — 30 comptes EUR/USD lus en détail
    for a in json.loads((ROOT / "traders_eurusd" / "accounts.json").read_text())["accounts"]:
        dd = max([v for v in (a["dd_bal_max"], a["dd_eq_rel"]) if v is not None] or [None]) if (a["dd_bal_max"] or a["dd_eq_rel"]) else None
        risk = [f for f in a["risk_flags"] if any(w in f for w in GRID_WORDS)]
        rows[a["id"]] = dict(source="MQL5 Signals", nom=a["name"], url=f"https://www.mql5.com/en/signals/{a['id']}", niveau="B",
                             type_compte=("réel (nom du serveur)" if a["server"] and any(k in a["server"].lower() for k in ("live", "real")) else "non indiqué"),
                             anciennete=f"{a['weeks']} semaines" if a["weeks"] else "?", instruments=a["pairs"], trades=a["trades"],
                             pf=a["pf"], dd_pct=dd, rendement="", regles_publiques=a["strategy"],
                             risque="; ".join(risk), historique="non")
    # A — historiques exportés (gestion des positions mesurée)
    for f, key in ((ROOT / "traders_eurusd" / "histories" / "live_eurusd.json", "trader"), (ROOT / "calm_pairs" / "profils_paires_calmes.json", "trader")):
        for p in json.loads(f.read_text()):
            sid = p["signal"].rstrip("/").split("/")[-1]
            r = rows.get(sid, dict(source="MQL5 Signals", nom=p[key], url=p["signal"], type_compte="réel (nom du serveur)",
                                   anciennete="", instruments=", ".join(p.get("paires", {}).keys()), trades=p.get("positions"),
                                   pf=p.get("pf_trades_fermes"), dd_pct=None, rendement="", regles_publiques="non publiées"))
            add = p.get("ajouts_a_prix_pire_pct")
            r.update(niveau="A", historique="oui (export MQL5)")
            if p.get("pf_eurusd") is not None:
                r["pf_eurusd_reel"] = p["pf_eurusd"]
            r["risque"] = (f"{add} % d'ajouts à un prix pire" if add is not None and add >= 20 else r.get("risque", "")) or ""
            rows[sid] = r
    # C — lignes de listes MQL5
    for name, sid, growth, dd, weeks, trades, pf in MQL5_LIST:
        sid = str(sid)
        if sid in rows:
            continue
        rows[sid] = dict(source="MQL5 Signals (liste)", nom=name, url=f"https://www.mql5.com/en/signals/{sid}", niveau="C",
                         type_compte="non vérifié", anciennete=f"{weeks} semaines", instruments="non vérifié", trades=trades, pf=pf,
                         dd_pct=dd, rendement=f"+{growth} % (croissance totale)", regles_publiques="non lues", risque="", historique="non")
    for name, sym, roi, age in CTRADER:
        rows[f"ct-{name}"] = dict(source="cTrader Copy", nom=name, url="https://ctrader.com/copy/symbols/eurusd", niveau="D",
                                  type_compte="non indiqué", anciennete=age, instruments=sym, trades=None, pf=None, dd_pct=None,
                                  rendement=f"{roi} % (ROI)", regles_publiques="non", risque="", historique="non")
    for name, gain, dd in MYFXBOOK:
        rows[f"mfx-{name}"] = dict(source="Myfxbook (liste)", nom=name, url="https://www.myfxbook.com/systems", niveau="D",
                                   type_compte="non indiqué", anciennete="?", instruments="?", trades=None, pf=None, dd_pct=dd,
                                   rendement=f"{gain} % (gain)", regles_publiques="non", risque="", historique="non (pages de compte refusées)")
    for name, sid, inst, trades, age, ann, dd in COLLECTIVE2:
        rows[f"c2-{sid}"] = dict(source="Collective2", nom=name, url=f"https://www.collective2.com/details-list/{sid}", niveau="H",
                                 type_compte="HYPOTHÉTIQUE (indiqué par le site)", anciennete=age, instruments=inst, trades=trades,
                                 pf=2.60 if sid == 134962085 else None, dd_pct=dd, rendement=f"{ann} %/an (hypothétique)",
                                 regles_publiques=("surachat/survente, stops rarement utilisés" if sid == 134962085 else "non"),
                                 risque=("stops rarement utilisés (auteur)" if sid == 134962085 else ""), historique="non")
    out = []
    for sid, r in rows.items():
        reasons = []
        if r["niveau"] == "H":
            reasons.append("performance hypothétique")
        if r["niveau"] == "D":
            reasons.append("données insuffisantes (pas de PF, trades ni drawdown)")
        if r.get("risque"):
            reasons.append("gestion à risque non borné : " + r["risque"])
        if r.get("pf_eurusd_reel") is not None and r["pf_eurusd_reel"] < 1.30:
            reasons.append(f"PF réel EUR/USD {r['pf_eurusd_reel']} < 1,30")
        if "backtest" in str(r.get("risque_info", "")) or r["nom"] == "EURUSD Quant Signal":
            reasons.append("chiffres présentés comme backtest, pas un compte suivi")
        if r["pf"] is not None and r["pf"] < 1.30:
            reasons.append("PF < 1,30")
        if r["dd_pct"] is not None and r["dd_pct"] > 15:
            reasons.append("drawdown > 15 %")
        if "EURUSD" not in str(r["instruments"]).upper().replace("/", "") and r["niveau"] in "ABC":
            reasons.append("EUR/USD non dominant ou non vérifié")
        rp = str(r["regles_publiques"]).lower()
        if rp in ("non", "non lues", "non publiées") or any(w in rp for w in ("non décrite", "aucune", "pas de règles", "règles non publiées", "non publi")) or r["nom"] == "EURUSD Quant Signal":
            reasons.append("règles non publiées")
        r["decision"] = "écarté" if reasons else "à étudier"
        r["raisons"] = " ; ".join(reasons)
        out.append(r)
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "H": 4}
    out.sort(key=lambda r: (order[r["niveau"]], r["source"], r["nom"]))
    cols = ["source", "nom", "url", "niveau", "type_compte", "anciennete", "instruments", "trades", "pf", "dd_pct", "rendement",
            "regles_publiques", "risque", "historique", "decision", "raisons"]
    for r in out:
        r.pop("pf_eurusd_reel", None)
    here = Path(__file__).resolve().parent
    with open(here / "catalogue_comptes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    stats = {}
    for r in out:
        stats.setdefault(r["source"], {}).setdefault(r["niveau"], 0)
        stats[r["source"]][r["niveau"]] += 1
    print(f"{len(out)} comptes ; à étudier : {sum(r['decision'] == 'à étudier' for r in out)}")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    main()
