"""Profil de gestion des positions de chaque trader (toutes paires) à partir de son historique MQL5 exporté.

Observé uniquement : stop posé, objectif, renforts à prix pire, volume croissant dans les paniers,
positions simultanées, performance des trades fermés par année.
Usage : python profiles.py <dossier_csv> → profils_paires_calmes.json
"""
from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "traders_eurusd" / "histories"))
from analyze import load_deals, load_positions  # noqa: E402

NAMES = {"2378478": "LazyProV2 AUDCAD", "2373736": "Steady Long term", "2341479": "Ultimate AUDCAD HAWK",
         "2339857": "Calm Waters", "840474": "MySingalStart 2", "1750952": "Cradle", "1750918": "Black Mountain",
         "2274644": "Pinnacle Alpha"}
PIP = {"JPY": 0.01}


def pipsize(sym):
    return 0.01 if "JPY" in sym.upper() else 0.0001


def profile(df, name):
    e = df[df["type"].isin(["Buy", "Sell"])].copy()
    e["sym"] = e["symbol"].str.upper().str.replace(r"[^A-Z]", "", regex=True).str[:6]
    e["side"] = np.where(e["type"] == "Buy", 1, -1)
    e["net"] = e["profit"].fillna(0) + e["commission"].fillna(0) + e["swap"].fillna(0)
    e["ps"] = e["sym"].map(pipsize)
    e["sl_pips"] = (e["price"] - e["sl"]).abs() / e["ps"]
    e["tp_pips"] = (e["tp"] - e["price"]).abs() / e["ps"]
    e["hold_h"] = (e["t_close"] - e["t_open"]).dt.total_seconds() / 3600
    e = e.sort_values("t_open").reset_index(drop=True)
    first = worse = better = 0
    max_same = 0
    for (sym, typ), g in e.groupby(["sym", "type"]):
        to, tc, pr = g["t_open"].to_numpy(), g["t_close"].to_numpy(), g["price"].to_numpy()
        side = 1 if typ == "Buy" else -1
        for k in range(len(g)):
            openm = (to[:k] < to[k]) & (tc[:k] > to[k])
            n = int(openm.sum())
            max_same = max(max_same, n + 1)
            if n == 0:
                first += 1
            elif (pr[k] - pr[:k][openm][0]) * side < 0:
                worse += 1
            else:
                better += 1
    grp = e.groupby(["sym", "t_close", "close", "side"])
    sizes = grp.size()
    baskets = sizes[sizes > 1]
    vol_up = 0
    for key in baskets.index:
        v = grp.get_group(key).sort_values("t_open")["volume"].to_numpy()
        vol_up += int((np.diff(v) > 0).any())
    sl_set = e["sl"].notna() & (e["sl"] > 0)
    tp_set = e["tp"].notna() & (e["tp"] > 0)
    gp, gl = e.loc[e.net > 0, "net"].sum(), -e.loc[e.net < 0, "net"].sum()
    years = {}
    for y, g in e.groupby(e["t_close"].dt.year):
        a, b = g.net[g.net > 0].sum(), -g.net[g.net < 0].sum()
        years[int(y)] = {"trades": int(len(g)), "pf": round(a / b, 2) if b > 0 else None, "net": round(float(g.net.sum()), 2)}
    tot = first + worse + better
    return {
        "trader": name, "positions": int(len(e)),
        "periode": f"{e['t_open'].min():%Y-%m} → {e['t_close'].max():%Y-%m}",
        "paires": {k: round(100 * v, 1) for k, v in e["sym"].value_counts(normalize=True).head(5).items()},
        "stop_pose_pct": round(100 * float(sl_set.mean()), 1),
        "stop_pips_mediane": round(float(e.loc[sl_set, "sl_pips"].median()), 1) if sl_set.any() else None,
        "objectif_pose_pct": round(100 * float(tp_set.mean()), 1),
        "objectif_pips_mediane": round(float(e.loc[tp_set, "tp_pips"].median()), 1) if tp_set.any() else None,
        "duree_h_mediane": round(float(e["hold_h"].median()), 1), "duree_h_max": round(float(e["hold_h"].max()), 0),
        "pf_trades_fermes": round(gp / gl, 2) if gl > 0 else None, "reussite_pct": round(100 * float((e.net > 0).mean()), 1),
        "ajouts_a_prix_pire_pct": round(100 * worse / max(tot, 1), 1),
        "ajouts_a_prix_meilleur_pct": round(100 * better / max(tot, 1), 1),
        "max_positions_meme_sens_meme_paire": max_same,
        "paniers": int(len(baskets)), "paniers_volume_croissant": vol_up,
        "pire_trade": round(float(e.net.min()), 2), "gain_moyen": round(float(e.loc[e.net > 0, "net"].mean()), 2),
        "annees": years, "annees_perdantes": [y for y, v in years.items() if v["net"] < 0],
    }


def main(folder):
    res = []
    for f in sorted(Path(folder).glob("*.csv")):
        sid = re.search(r"(\d{6,7})\.history", f.name).group(1)
        head = f.read_text(encoding="utf-8-sig").splitlines()[0]
        df = load_deals(f) if "Direction" in head else load_positions(f)
        p = profile(df, NAMES.get(sid, sid))
        p["signal"] = f"https://www.mql5.com/en/signals/{sid}"
        res.append(p)
        print(json.dumps(p, ensure_ascii=False))
    (Path(__file__).parent / "profils_paires_calmes.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
