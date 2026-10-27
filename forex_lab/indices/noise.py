"""Test I01 — stratégie « zone de bruit » (Zarattini, Aziz, Barbon 2024) sur le CFD S&P 500, selon PROTOCOLE.md.

Usage : python -m forex_lab.indices.noise --session data/session.csv.gz
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
N = 390
CHECKS = list(range(30, 361, 30))          # 10:00 … 15:30 (minutes depuis 09:30)
LOOKBACK = 14
SLIP = {"standard": 0.1, "stress": 0.6}     # points par ordre
REPRO = ("2016-01-01", "2024-04-30")
POST = ("2024-05-01", "2026-12-31")
POST_SUBS = {"mai-déc. 2024": ("2024-05-01", "2024-12-31"), "2025": ("2025-01-01", "2025-12-31"), "2026": ("2026-01-01", "2026-12-31")}


def to_arrays(df: pd.DataFrame):
    days = sorted(df["jour"].unique())
    idx = {d: i for i, d in enumerate(days)}
    A = {c: np.full((len(days), N), np.nan) for c in ("bo", "bc", "ao", "ac", "h", "l", "v")}
    r = df["jour"].map(idx).to_numpy()
    m = df["m"].to_numpy().astype(int)
    for c in A:
        A[c][r, m] = df[c].to_numpy()
    A["mo"] = (A["bo"] + A["ao"]) / 2
    A["mc"] = (A["bc"] + A["ac"]) / 2
    return days, A


def last_valid(row: np.ndarray) -> float:
    ok = np.where(~np.isnan(row))[0]
    return row[ok[-1]] if len(ok) else np.nan


def simulate(days, A, slip: float):
    nd = len(days)
    open_ = A["mo"][:, 0]
    close = np.array([last_valid(A["mc"][i]) for i in range(nd)])
    move = np.abs(A["mc"] / open_[:, None] - 1)              # |Close(minute) / Open(09:30) − 1|
    tp = (A["h"] + A["l"] + A["mc"]) / 3
    vol = np.nan_to_num(A["v"])
    w = np.where(np.isnan(tp), 0, vol)
    num = np.cumsum(np.nan_to_num(tp) * w, axis=1)
    den = np.cumsum(w, axis=1)
    # repli : moyenne simple si aucun volume
    cnt = np.cumsum(~np.isnan(tp), axis=1)
    twap = np.cumsum(np.nan_to_num(tp), axis=1) / np.maximum(cnt, 1)
    vwap = np.where(den > 0, num / np.where(den > 0, den, 1), twap)
    no_vol_days = int(((den[:, -1] == 0) & (cnt[:, -1] > 0)).sum())
    dates = pd.to_datetime(pd.Series(days))
    out = []
    for i in range(nd):
        rec = {"jour": days[i], "r": 0.0, "trades": 0, "gagnants": 0, "actif": False}
        if (i < LOOKBACK or np.isnan(open_[i]) or np.isnan(close[i - 1])
                or (dates[i] - dates[i - LOOKBACK]).days > 30):
            out.append(rec)
            continue
        hist = move[i - LOOKBACK:i]
        rec["actif"] = True
        top, bot = max(open_[i], close[i - 1]), min(open_[i], close[i - 1])
        pos, entry = 0, 0.0
        trades = []

        def close_pos(px_exit):
            nonlocal pos
            r = (px_exit - entry) / entry if pos > 0 else (entry - px_exit) / entry
            trades.append(r)
            pos = 0

        for T in CHECKS:
            p = A["mc"][i, T - 1]
            sig_col = hist[:, T - 1]
            if np.isnan(p) or np.isnan(A["bo"][i, T]) or np.isnan(sig_col).any():
                continue
            s = sig_col.mean()
            ub, lb, vw = top * (1 + s), bot * (1 - s), vwap[i, T - 1]
            buy_px, sell_px = A["ao"][i, T] + slip, A["bo"][i, T] - slip
            stopped = 0
            if pos > 0 and p < max(ub, vw):
                close_pos(sell_px); stopped = 1
            elif pos < 0 and p > min(lb, vw):
                close_pos(buy_px); stopped = -1
            if pos == 0:
                if p > ub and stopped != 1:
                    pos, entry = 1, buy_px
                elif p < lb and stopped != -1:
                    pos, entry = -1, sell_px
        if pos != 0:
            ok = np.where(~np.isnan(A["bc"][i]))[0]
            k = ok[-1]
            close_pos(A["bc"][i, k] - slip if pos > 0 else A["ac"][i, k] + slip)
        rec.update(r=float(sum(trades)), trades=len(trades), gagnants=int(sum(t > 0 for t in trades)))
        out.append(rec)
    res = pd.DataFrame(out).set_index("jour")
    # taille dynamique (information) : min(4, 2 % / vol. journalière 14 j), vol. calculée sur les clôtures 16:00 passées
    dret = pd.Series(close, index=days).pct_change()
    sd = dret.rolling(LOOKBACK).std(ddof=1).shift(1)
    res["levier_dyn"] = np.minimum(4.0, 0.02 / sd).fillna(0).values
    res["r_dyn"] = res["r"] * res["levier_dyn"]
    res["indice"] = dret.values
    return res, no_vol_days


def stats(r: pd.Series, trades: pd.Series | None = None, win: pd.Series | None = None) -> dict:
    r = r.dropna()
    if len(r) < 20:
        return {"jours": int(len(r))}
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    sd = r.std(ddof=1)
    out = {"jours": int(len(r)), "debut": r.index[0], "fin": r.index[-1],
           "rendement_total_pct": round(100 * (eq.iloc[-1] - 1), 1),
           "rendement_annuel_pct": round(100 * (eq.iloc[-1] ** (1 / yrs) - 1), 2),
           "sharpe": round(r.mean() / sd * math.sqrt(252), 2) if sd else None,
           "t": round(r.mean() / sd * math.sqrt(len(r)), 2) if sd else None,
           "perte_max_pct": round(100 * float((eq / eq.cummax() - 1).min()), 1)}
    if trades is not None:
        out["trades"] = int(trades.sum())
        out["taux_gain_pct"] = round(100 * float(win.sum() / max(trades.sum(), 1)), 1)
    return out


def window(df, a, b):
    return df[(df.index >= a) & (df.index <= b)]


def run(session: Path) -> dict:
    df = pd.read_csv(session)
    days, A = to_arrays(df)
    sims = {}
    nov = 0
    for k, s in SLIP.items():
        sims[k], nov = simulate(days, A, s)
    std, stress = sims["standard"], sims["stress"]
    act = std[std["actif"]]
    rep = {"repro": stats(window(act, *REPRO)["r"], window(act, *REPRO)["trades"], window(act, *REPRO)["gagnants"]),
           "post": stats(window(act, *POST)["r"], window(act, *POST)["trades"], window(act, *POST)["gagnants"]),
           "post_stress": stats(window(stress[stress["actif"]], *POST)["r"]),
           "post_sous_periodes": {k: stats(window(act, a, b)["r"]) for k, (a, b) in POST_SUBS.items()}}
    p, sp = rep["post"], rep["post_sous_periodes"]
    c0 = (rep["repro"].get("sharpe") or -9) >= 0.8
    crit = {"C0 reproduction Sharpe ≥ 0,8": c0,
            "C1 après publication > 0 et Sharpe ≥ 0,75": (p.get("rendement_total_pct") or -1) > 0 and (p.get("sharpe") or -9) >= 0.75,
            "C2 frais de stress > 0": (rep["post_stress"].get("rendement_total_pct") or -1) > 0,
            "C3 perte max ≤ 15 %": (p.get("perte_max_pct") or -100) >= -15,
            "C4 ≥ 2 sous-périodes sur 3 > 0": sum((v.get("rendement_total_pct") or -1) > 0 for v in sp.values()) >= 2}
    crit = {k: bool(v) for k, v in crit.items()}
    verdict = "PASSE" if all(crit.values()) else ("NON CONCLUANT (copie non conforme)" if not c0 else "ÉCHEC")
    yearly = {}
    for y in sorted({d[:4] for d in act.index}):
        sub = act[act.index.str.startswith(y)]
        yearly[y] = {"officiel_pct": round(100 * float((1 + sub["r"]).prod() - 1), 1),
                     "dynamique_pct": round(100 * float((1 + sub["r_dyn"]).prod() - 1), 1),
                     "indice_pct": round(100 * float((1 + sub["indice"].fillna(0)).prod() - 1), 1)}
    return {"protocole": "forex_lab/indices/PROTOCOLE.md", "jours_sans_volume": nov, "jours": len(days),
            "officiel_1x": rep, "criteres": crit, "verdict": verdict,
            "info_dynamique": {"repro": stats(window(act, *REPRO)["r_dyn"]), "post": stats(window(act, *POST)["r_dyn"])},
            "info_indice_achete_garde": {"repro": stats(window(act, *REPRO)["indice"]), "post": stats(window(act, *POST)["indice"])},
            "par_annee": yearly,
            "serie": [{"jour": d, "r_pct": round(100 * r, 4)} for d, r in act["r"].items()]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="data/session.csv.gz")
    ap.add_argument("--out", default=str(HERE / "resultats.json"))
    a = ap.parse_args()
    res = run(Path(a.session))
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    print(json.dumps({k: res[k] for k in ("criteres", "verdict")}, ensure_ascii=False, indent=1))
    print(json.dumps(res["officiel_1x"], ensure_ascii=False, indent=1, default=str))
    print(json.dumps(res["par_annee"], ensure_ascii=False))
    print(f"::notice::verdict {res['verdict']} — après publication : {res['officiel_1x']['post']}")


if __name__ == "__main__":
    main()
