"""Analyse des historiques MQL5 exportés (CSV) des 5 traders — ce qui est OBSERVÉ, rien d'inventé.

Les fichiers bruts ne sont pas versionnés (données exportées depuis un compte MQL5 personnel ;
dépôt public). Usage : python analyze.py <dossier_des_csv> → profils.json + profils.md
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

NAMES = {"1750957": "Kosciuszko", "2367606": "EUR Trader 2", "1932739": "TP TRADER",
         "2378489": "EansPRO V3 EURUSD", "2385213": "WolvesVN EU"}


def num(s):
    if pd.isna(s) or str(s).strip() == "":
        return np.nan
    return float(str(s).replace(" ", "").replace(" ", ""))


def load_positions(path):
    raw = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    raw.columns = ["t_open", "type", "volume", "symbol", "price", "sl", "tp", "t_close", "close", "commission", "swap", "profit", "comment"]
    for c in ("volume", "price", "sl", "tp", "close", "commission", "swap", "profit"):
        raw[c] = raw[c].map(num)
    raw["t_open"] = pd.to_datetime(raw["t_open"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    raw["t_close"] = pd.to_datetime(raw["t_close"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    raw["comment"] = raw["comment"].fillna("")
    return raw


def load_deals(path):
    """Format « deals » (EUR Trader 2) : reconstitue les positions In/Out par appariement FIFO."""
    d = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    d.columns = ["time", "symbol", "type", "direction", "volume", "price", "commission", "swap", "profit", "comment"]
    d = d[d["direction"].isin(["In", "Out"])].copy()
    for c in ("volume", "price", "commission", "swap", "profit"):
        d[c] = d[c].map(num)
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S")
    d = d.sort_values("time", kind="stable")
    open_pos, rows = {}, []
    for _, r in d.iterrows():
        key = r["symbol"]
        if r["direction"] == "In":
            open_pos.setdefault(key, []).append(r)
            continue
        side_out = r["type"]          # une sortie « Buy » ferme une vente
        want = "Sell" if side_out == "Buy" else "Buy"
        lst = open_pos.get(key, [])
        idx = next((i for i, x in enumerate(lst) if x["type"] == want), None)
        if idx is None:
            continue
        o = lst.pop(idx)
        sl_m = re.search(r"\[sl", str(r["comment"]) if isinstance(r["comment"], str) else "")
        tp_m = re.search(r"\[tp", str(r["comment"]) if isinstance(r["comment"], str) else "")
        rows.append({"t_open": o["time"], "type": want, "volume": o["volume"], "symbol": key, "price": o["price"],
                     "sl": np.nan, "tp": np.nan, "t_close": r["time"], "close": r["price"],
                     "commission": (o["commission"] or 0) + (r["commission"] or 0), "swap": r["swap"],
                     "profit": r["profit"], "comment": "[sl]" if sl_m else "[tp]" if tp_m else ""})
    return pd.DataFrame(rows)


def pip(sym, price):
    return 0.01 if "JPY" in sym else (0.1 if price > 500 else 0.0001)


def profile(df, name):
    ex = df[df["type"].isin(["Buy", "Sell"])].copy()
    pend = df[df["type"].str.contains("Stop|Limit", na=False)]
    ex["eur"] = ex["symbol"].str.upper().str.startswith("EURUSD")
    e = ex[ex["eur"]].copy()
    e["side"] = np.where(e["type"] == "Buy", 1, -1)
    p = 0.0001
    e["hold_h"] = (e["t_close"] - e["t_open"]).dt.total_seconds() / 3600
    e["sl_pips"] = (e["price"] - e["sl"]).abs() / p
    e["tp_pips"] = (e["tp"] - e["price"]).abs() / p
    e["res_pips"] = (e["close"] - e["price"]) * e["side"] / p
    e["net"] = e["profit"].fillna(0) + e["commission"].fillna(0) + e["swap"].fillna(0)
    e["exit"] = e["comment"].str.extract(r"\[(sl|tp)")[0].fillna("manuel/autre")
    # paniers : positions de même sens fermées à la même seconde au même prix
    grp = e.groupby(["t_close", "close", "side"]).size()
    basket_share = float((grp[grp > 1].sum()) / len(e)) if len(e) else 0
    # positions ouvertes simultanément (même sens) et évolution des volumes dans le panier
    ev = pd.concat([pd.DataFrame({"t": e["t_open"], "d": 1, "s": e["side"]}),
                    pd.DataFrame({"t": e["t_close"], "d": -1, "s": e["side"]})]).sort_values(["t", "d"])
    max_same = 0
    for s in (1, -1):
        c = ev[ev["s"] == s]["d"].cumsum()
        max_same = max(max_same, int(c.max()) if len(c) else 0)
    vol_up = 0
    multi = grp[grp > 1].index
    for k in multi:
        g = e.set_index(["t_close", "close", "side"]).loc[k].sort_values("t_open")
        v = g["volume"].to_numpy()
        if len(v) > 1 and (np.diff(v) > 0).any():
            vol_up += 1
    sl_set = e["sl"].notna() & (e["sl"] > 0)
    tp_set = e["tp"].notna() & (e["tp"] > 0)
    gp = e.loc[e["net"] > 0, "net"].sum()
    gl = -e.loc[e["net"] < 0, "net"].sum()
    hours = e["t_open"].dt.hour.value_counts(normalize=True).sort_index()
    on_round = float((e["t_open"].dt.second.eq(0) & e["t_open"].dt.minute.isin([0, 5, 15, 30, 45])).mean())
    best = e["net"].max()
    out = {
        "trader": name, "positions_toutes_paires": int(len(ex)), "positions_eurusd": int(len(e)),
        "part_eurusd_pct": round(100 * len(e) / max(len(ex), 1), 1),
        "periode": f"{e['t_open'].min():%Y-%m-%d} → {e['t_close'].max():%Y-%m-%d}" if len(e) else "",
        "ordres_en_attente_tous": int(len(pend)),
        "types_ordres_en_attente": pend["type"].value_counts().to_dict(),
        "stop_pose_pct": round(100 * sl_set.mean(), 1), "objectif_pose_pct": round(100 * tp_set.mean(), 1),
        "stop_pips_mediane": round(float(e.loc[sl_set, "sl_pips"].median()), 1) if sl_set.any() else None,
        "objectif_pips_mediane": round(float(e.loc[tp_set, "tp_pips"].median()), 1) if tp_set.any() else None,
        "stop_pips_valeurs_frequentes": e.loc[sl_set, "sl_pips"].round(0).value_counts().head(5).to_dict(),
        "objectif_pips_valeurs_frequentes": e.loc[tp_set, "tp_pips"].round(0).value_counts().head(5).to_dict(),
        "duree_h_mediane": round(float(e["hold_h"].median()), 2), "duree_h_p90": round(float(e["hold_h"].quantile(0.9)), 1),
        "sorties": e["exit"].value_counts().to_dict(),
        "reussite_pct": round(100 * float((e["net"] > 0).mean()), 1),
        "profit_factor_eurusd": round(gp / gl, 2) if gl > 0 else None,
        "resultat_net_eurusd": round(float(e["net"].sum()), 2),
        "meilleur_trade_part_du_net_pct": round(100 * best / e["net"].sum(), 1) if e["net"].sum() > 0 else None,
        "achats_pct": round(100 * float((e["side"] > 0).mean()), 1),
        "volumes_frequents": e["volume"].value_counts().head(4).to_dict(),
        "positions_fermees_en_panier_pct": round(100 * basket_share, 1),
        "max_positions_meme_sens_simultanees": max_same,
        "paniers_avec_volume_croissant": int(vol_up), "paniers": int(len(multi)),
        "entrees_a_heure_ronde_pct": round(100 * on_round, 1),
        "heures_entree_top": {int(k): round(100 * v, 1) for k, v in hours.sort_values(ascending=False).head(6).items()},
    }
    return out, e


def main(folder):
    folder = Path(folder)
    res, all_e = [], {}
    for f in sorted(folder.glob("*.csv")):
        sid = re.search(r"(\d{6,7})\.history", f.name).group(1)
        name = NAMES.get(sid, sid)
        head = f.read_text(encoding="utf-8-sig").splitlines()[0]
        df = load_deals(f) if "Direction" in head else load_positions(f)
        prof, e = profile(df, name)
        prof["signal"] = f"https://www.mql5.com/en/signals/{sid}"
        res.append(prof)
        all_e[name] = e
        print(json.dumps(prof, ensure_ascii=False, default=str))
    out = Path(__file__).parent
    (out / "profils.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    return res, all_e


if __name__ == "__main__":
    main(sys.argv[1])
