"""Simulation de COPIE d'un trader à partir de son historique MQL5 exporté — aucun ordre réel.

Règle de copie (comme le copieur MQL5) : lot copié = lot du trader × (notre solde / son solde), arrondi à 0,01.
Si le lot copié tombe sous 0,01 : variante « ignorer » (trade non copié) et variante « forcer 0,01 » (risque gonflé).
Son solde est reconstitué : dépôts/retraits (lignes Balance) + résultats des trades déjà fermés.
Limite : seuls les trades FERMÉS sont connus ; les pertes latentes (positions ouvertes) ne sont pas visibles,
donc le drawdown réel d'une copie peut être plus grand que celui calculé ici.

Usage : python copy_sim.py <csv> [capital=150]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "traders_eurusd" / "histories"))
from analyze import load_deals, load_positions, num  # noqa: E402


def balance_events(path):
    raw = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    head = raw.columns.tolist()
    if "Direction" in head:
        b = raw[raw["Type"] == "Balance"]
        return pd.DataFrame({"t": pd.to_datetime(b["Time"], format="%Y.%m.%d %H:%M:%S"), "amount": b["Profit"].map(num)})
    raw.columns = ["t_open", "type", "volume", "symbol", "price", "sl", "tp", "t_close", "close", "commission", "swap", "profit", "comment"]
    b = raw[raw["type"].isin(["Balance", "Credit"])]
    return pd.DataFrame({"t": pd.to_datetime(b["t_open"], format="%Y.%m.%d %H:%M:%S"), "amount": b["profit"].map(num)})


def simulate(path, capital=150.0):
    head = Path(path).read_text(encoding="utf-8-sig").splitlines()[0]
    df = load_deals(path) if "Direction" in head else load_positions(path)
    tr = df[df["type"].isin(["Buy", "Sell"])].copy()
    tr["net"] = tr["profit"].fillna(0) + tr["commission"].fillna(0) + tr["swap"].fillna(0)
    bal = balance_events(path).sort_values("t")
    # événements chronologiques : ouverture (calcul du lot) et fermeture (résultat)
    tr = tr.sort_values("t_open").reset_index(drop=True)
    closes = tr.sort_values("t_close")
    import heapq
    bal_t = bal["t"].to_numpy(); bal_c = np.cumsum(bal["amount"].fillna(0).to_numpy())
    cl_t = closes["t_close"].to_numpy(); cl_c = np.cumsum(closes["net"].to_numpy())
    def their_balance(t):
        i = np.searchsorted(bal_t, np.datetime64(t), side="right"); j = np.searchsorted(cl_t, np.datetime64(t), side="right")
        return (bal_c[i - 1] if i else 0.0) + (cl_c[j - 1] if j else 0.0)
    out = {}
    for mode in ("ignorer", "forcer_0.01"):
        copied = skipped = forced = 0
        realized, pending, lots = 0.0, [], {}
        for i, r in tr.iterrows():
            while pending and pending[0][0] <= r["t_open"]:
                realized += heapq.heappop(pending)[1]
            their = their_balance(r["t_open"])
            ours_now = capital + realized
            if their <= 0 or ours_now <= 0 or not r["volume"]:
                skipped += 1
                continue
            lot = round(r["volume"] * ours_now / their, 2)
            if lot < 0.01:
                if mode == "ignorer":
                    skipped += 1
                    continue
                lot, forced = 0.01, forced + 1
            pnl = r["net"] * lot / r["volume"]
            lots[i] = {"t_close": r["t_close"], "pnl": pnl}
            heapq.heappush(pending, (r["t_close"], pnl, i))
            copied += 1
        seq = sorted(lots.values(), key=lambda v: v["t_close"])
        eq = capital + np.cumsum([v["pnl"] for v in seq]) if seq else np.array([capital])
        peaks = np.maximum.accumulate(np.concatenate([[capital], eq]))[1:]
        dd = float(np.max((peaks - eq) / peaks)) * 100 if len(eq) else 0.0
        out[mode] = {"capital_initial": capital, "capital_final": round(float(eq[-1]), 2),
                     "rentabilite_pct": round((float(eq[-1]) / capital - 1) * 100, 1),
                     "drawdown_max_trades_fermes_pct": round(dd, 1), "trades_copies": copied,
                     "trades_non_copies": skipped, "lots_forces_a_0_01": forced,
                     "minimum_capital": round(float(eq.min()), 2),
                     "periode": f"{tr['t_open'].min():%Y-%m} → {tr['t_close'].max():%Y-%m}"}
    return out


if __name__ == "__main__":
    cap = float(sys.argv[2]) if len(sys.argv) > 2 else 150.0
    print(json.dumps(simulate(sys.argv[1], cap), indent=2, ensure_ascii=False))
