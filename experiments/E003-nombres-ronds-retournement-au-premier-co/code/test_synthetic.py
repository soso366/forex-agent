"""E003 — test synthétique (données FABRIQUÉES en mémoire, aucune donnée de marché lue).

Vérifie (exigences 3 et 4 du Critic) :
1. ATR sans fuite : pour un contact à hh:07, l'ATR utilisée = ATR de la barre M5 hh:00–hh:04 ; perturber toutes les
   minutes >= t0 (y compris t0) ne change pas l'ATR à t0 ; l'ATR « naïve » (étiquette de début M5) change, ce qui
   prouve que le test détecte la fuite.
2. Premier contact : signal à la bonne minute, bon sens, bon niveau, entrée à t+1 ; second contact 30 min plus tard
   ignoré ; perturbation du futur (> t0) sans effet sur le signal à t0.
3. Fenêtre de 120 min en temps d'HORLOGE : un contact 121 min avant (avec 30 minutes manquantes dans la fenêtre)
   n'empêche pas le signal (une fenêtre en rangs de lignes l'aurait bloqué) ; un contact avant 07:00 mais dans les
   120 min bloque le signal (les minutes hors 07–19:30 comptent).
4. Minute t+1 absente → aucun signal ; contact « créé par le spread » repéré ; grille placebo +17 distincte.
5. Sortie forcée 20:00 : contact à 19:30 avec H = 30 → durée 29 min ; stress au pire prix <= R simulé.
Exécution : python3 experiments/E003-…/code/test_synthetic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e003 import (PairData, atr, bars, candidates, level_above, level_below, select,  # noqa: E402
                  simulate_trades)

P = 1e-4
HALF = 0.1 * P
COLS = ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")


def _ts(s):
    return pd.Timestamp(s, tz="UTC")


def build(days, keypoints, overrides=None, delete=(), ask_high=None):
    """Série M1 fabriquée : chemin mid linéaire par morceaux + zigzag ±0,8 pip ; spread 0,2 pip.
    overrides : {temps: (close, high, low)} sur le mid ; ask_high : {temps: valeur} (contact « de spread »)."""
    idx = pd.DatetimeIndex([])
    for d in days:
        idx = idx.append(pd.date_range(_ts(d), periods=1440, freq="1min"))
    kp = pd.Series({_ts(k): v for k, v in keypoints.items()}).sort_index()
    x = idx.asi8.astype(float)
    path = np.interp(x, kp.index.asi8.astype(float), kp.to_numpy())
    c = path + 0.8 * P * np.where(np.arange(len(idx)) % 2 == 0, 1.0, -1.0)
    ov = {_ts(k): v for k, v in (overrides or {}).items()}
    pos = {t: idx.get_loc(t) for t in ov}
    for t, (cc, _, _) in ov.items():
        c[pos[t]] = cc
    o = np.concatenate([[c[0]], c[:-1]])
    h = np.maximum(o, c) + 0.3 * P
    lo = np.minimum(o, c) - 0.3 * P
    for t, (_, hh, ll) in ov.items():
        h[pos[t]], lo[pos[t]] = hh, ll
    df = pd.DataFrame({"bo": o - HALF, "bh": h - HALF, "bl": lo - HALF, "bc": c - HALF,
                       "ao": o + HALF, "ah": h + HALF, "al": lo + HALF, "ac": c + HALF}, index=idx)
    for t, v in (ask_high or {}).items():
        df.loc[_ts(t), "ah"] = v
    df = df.drop(index=[_ts(t) for t in delete], errors="ignore")
    df.index.name = "time"
    df["mid"] = (df["bc"] + df["ac"]) / 2
    df["spread"] = df["ac"] - df["bc"]
    return df


def _perturb(df, t0, strict_after, seed=3):
    rng = np.random.default_rng(seed)
    df = df.copy()
    m = (df.index > t0) if strict_after else (df.index >= t0)
    k = rng.normal(0, 0.002, m.sum())
    for col in COLS:
        df.loc[m, col] = df.loc[m, col].to_numpy() * (1 + k)
    df.loc[m, "ah"] = df.loc[m, "ah"] + 5 * P            # le futur touche tous les niveaux proches
    df.loc[m, "bl"] = df.loc[m, "bl"] - 5 * P
    df["mid"] = (df["bc"] + df["ac"]) / 2
    return df


def lookahead_checks(df, sym, t0) -> dict:
    """Utilisé aussi sur données réelles par run.py train."""
    base = PairData(df, sym)
    p0 = int(base.grid.get_loc(t0))
    r = {"t0": str(t0)}
    # ATR à t0 = ATR de la dernière barre M5 dont la fin <= t0
    a = atr(bars(df, "5min"), 14)
    done = a[a.index + pd.Timedelta(minutes=5) <= t0]          # barres terminées au plus tard au début de t0
    r["atr_bar_used"] = str(done.index[-1])
    r["atr_is_bar_ending_before_t0"] = bool(np.isclose(base.atr[p0], done.iloc[-1])
                                            and done.index[-1] <= t0.floor("5min") - pd.Timedelta(minutes=5))
    pert = PairData(_perturb(df, t0, strict_after=False), sym)
    r["atr_unchanged_when_t0_and_future_perturbed"] = bool(np.isclose(base.atr[p0], pert.atr[p0]))
    naive = a.reindex([t0], method="ffill").iloc[0]
    naive_p = atr(bars(_perturb(df, t0, strict_after=False), "5min"), 14).reindex([t0], method="ffill").iloc[0]
    r["sanity_naive_atr_leaks"] = bool(not np.isclose(naive, naive_p))
    p2 = PairData(_perturb(df, t0, strict_after=True), sym)
    for name in ("pmax", "pmin"):
        k = 0 if name == "pmax" else 1
        r[f"{name}_120_unchanged"] = bool(np.allclose(base.prev_extremes(120)[k][: p0 + 1],
                                                      p2.prev_extremes(120)[k][: p0 + 1], equal_nan=True))
    r["mc_ff_t-15_unchanged"] = bool(np.allclose(base.mc_ff[: p0 + 1], p2.mc_ff[: p0 + 1], equal_nan=True))
    r["pass"] = all(v for k, v in r.items() if k != "t0")
    return r


def run_all() -> dict:
    res = {}
    days = ["2025-09-02", "2025-09-03", "2025-09-04", "2025-09-05", "2025-09-08", "2025-09-09"]
    L1, L2 = 1.1700, 1.1650
    kp = {"2025-09-02 00:00": 1.1680,
          # jour A (mer.) : approche par le bas de 1,1700, contact 10:00, second contact 10:30
          "2025-09-03 09:40": 1.1680, "2025-09-03 09:59": L1 - 4 * P, "2025-09-03 10:00": L1 - 1 * P,
          "2025-09-03 10:20": 1.1685, "2025-09-03 10:29": L1 - 4 * P, "2025-09-03 10:30": L1 - 1 * P,
          "2025-09-03 11:00": 1.1680, "2025-09-03 23:59": 1.1680,
          # jour B (jeu.) : contact de 1,1650 à 05:00, 30 minutes manquantes, approche par le haut, contact 07:01
          "2025-09-04 00:00": 1.1660, "2025-09-04 04:50": 1.1660, "2025-09-04 04:59": L2 + 4 * P,
          "2025-09-04 05:00": L2 + 1 * P, "2025-09-04 05:01": L2 + 4 * P, "2025-09-04 05:30": 1.1660,
          "2025-09-04 06:45": 1.1660, "2025-09-04 07:00": L2 + 4 * P, "2025-09-04 07:01": L2 + 1 * P,
          "2025-09-04 07:30": 1.1660, "2025-09-04 23:59": 1.1660,
          # jour C (ven.) : contact 05:30 (avant 07:00, dans les 120 min), approche, contact 07:10 → bloqué
          "2025-09-05 00:00": 1.1660, "2025-09-05 05:20": 1.1660, "2025-09-05 05:29": L2 + 4 * P,
          "2025-09-05 05:30": L2 + 1 * P, "2025-09-05 05:31": L2 + 4 * P, "2025-09-05 06:00": 1.1660,
          "2025-09-05 06:54": 1.1660, "2025-09-05 07:09": L2 + 4 * P, "2025-09-05 07:10": L2 + 1 * P,
          "2025-09-05 07:40": 1.1660,
          # jour D (lun.) : comme A mais minute t+1 (10:01) absente ; contact de spread à 14:00 ; contact 19:30
          "2025-09-08 00:00": 1.1680, "2025-09-08 09:40": 1.1680, "2025-09-08 09:59": L1 - 4 * P,
          "2025-09-08 10:00": L1 - 1 * P, "2025-09-08 10:20": 1.1680, "2025-09-08 13:40": 1.1680,
          "2025-09-08 13:59": L1 - 4 * P, "2025-09-08 14:00": L1 - 2.5 * P, "2025-09-08 14:20": 1.1680,
          "2025-09-08 19:10": 1.1680, "2025-09-08 19:29": L1 - 4 * P, "2025-09-08 19:30": L1 - 1 * P,
          "2025-09-08 19:50": 1.1680, "2025-09-09 23:59": 1.1680}
    ov = {"2025-09-03 10:00": (L1 - 1 * P, L1 - 0.4 * P, L1 - 4.2 * P),
          "2025-09-03 10:30": (L1 - 1 * P, L1 - 0.4 * P, L1 - 4.2 * P),
          "2025-09-04 05:00": (L2 + 1 * P, L2 + 4.2 * P, L2 + 0.4 * P),
          "2025-09-04 07:01": (L2 + 1 * P, L2 + 4.2 * P, L2 + 0.4 * P),
          "2025-09-05 05:30": (L2 + 1 * P, L2 + 4.2 * P, L2 + 0.4 * P),
          "2025-09-05 07:10": (L2 + 1 * P, L2 + 4.2 * P, L2 + 0.4 * P),
          "2025-09-08 10:00": (L1 - 1 * P, L1 - 0.4 * P, L1 - 4.2 * P),
          "2025-09-08 14:00": (L1 - 2.5 * P, L1 - 2 * P, L1 - 4.2 * P),
          "2025-09-08 19:30": (L1 - 1 * P, L1 - 0.4 * P, L1 - 4.2 * P)}
    missing = [f"2025-09-04 {h:02d}:{m:02d}" for h, m in [(5, mm) for mm in range(40, 60)] + [(6, mm) for mm in range(0, 10)]]
    missing.append("2025-09-08 10:01")
    df = build(days, kp, ov, delete=missing, ask_high={"2025-09-08 14:00": L1 - 0.4 * P + HALF})
    f = PairData(df, "EURUSD")
    c = candidates(f, H=20)
    got = {str(t): (int(d), round(lv, 5), bool(sc)) for t, d, lv, sc in
           zip(c["contact_time"], c["dir"], c["L"], c["spread_contact"])}
    res["signals_found"] = got
    res["A_first_contact_10:00_sell_1.1700_entry_10:01"] = bool(
        got.get("2025-09-03 10:00:00+00:00") == (-1, 1.17, False)
        and (c.loc[c["contact_time"] == _ts("2025-09-03 10:00"), "time"] == _ts("2025-09-03 10:01")).all())
    res["A_second_contact_10:30_ignored"] = "2025-09-03 10:30:00+00:00" not in got
    res["B_clock_window_121min_with_gap_gives_buy_07:01"] = got.get("2025-09-04 07:01:00+00:00") == (1, 1.165, False)
    res["C_pre_0700_contact_within_120min_blocks_07:10"] = "2025-09-05 07:10:00+00:00" not in got
    res["D_missing_t+1_no_signal"] = "2025-09-08 10:00:00+00:00" not in got
    res["D_spread_contact_flagged"] = got.get("2025-09-08 14:00:00+00:00", (0, 0, False))[2] is True
    # contrôle de C : même approche SANS le contact de 05:30 → le signal de 07:10 existe (le blocage vient bien du
    # contact antérieur à 07:00, pas d'un autre filtre)
    kc = {"2025-09-02 00:00": 1.1660, "2025-09-05 06:54": 1.1660, "2025-09-05 07:09": L2 + 4 * P,
          "2025-09-05 07:10": L2 + 1 * P, "2025-09-05 07:40": 1.1660, "2025-09-05 23:59": 1.1660}
    dc = build(days[:4], kc, {"2025-09-05 07:10": ov["2025-09-05 07:10"]})
    cc = candidates(PairData(dc, "EURUSD"))
    res["C_control_without_0530_contact_gives_signal"] = bool((cc["contact_time"] == _ts("2025-09-05 07:10")).any())
    # ligne de rangs (contre-exemple) : une fenêtre de 120 LIGNES présentes inclurait le contact de 05:00
    pres = df.index[(df.index < _ts("2025-09-04 07:01"))][-120:]
    res["sanity_row_window_would_include_05:00"] = bool(_ts("2025-09-04 05:00") in pres)
    # sortie forcée 20:00
    c30 = candidates(f, H=30)
    h = c30.loc[c30["contact_time"] == _ts("2025-09-08 19:30"), "hold"]
    res["force_exit_19:30_H30_hold_29"] = bool(len(h) == 1 and int(h.iloc[0]) == 29)
    # placebo : grille +17 sans contact sur ces chemins ; fonctions de niveau
    res["placebo_+17_grid_no_signal"] = len(candidates(f, offset=17)) == 0
    res["level_functions"] = bool(np.isclose(level_above(1.16995, P, 0, 50), 1.17)
                                  and np.isclose(level_above(1.17, P, 0, 50), 1.1750)
                                  and np.isclose(level_below(1.16505, P, 0, 50), 1.165)
                                  and np.isclose(level_above(1.1668, P, 17, 50), 1.1717)
                                  and np.isclose(level_above(150.004, 1e-2, 0, 50), 150.5))
    # futur perturbé (> t0) : signal à t0 identique
    t0 = _ts("2025-09-03 10:00")
    c2 = candidates(PairData(_perturb(df, t0, strict_after=True), "EURUSD"), H=20)
    a0 = c.loc[c["contact_time"] == t0, ["dir", "L", "stop"]].to_numpy()
    b0 = c2.loc[c2["contact_time"] == t0, ["dir", "L", "stop"]].to_numpy()
    res["signal_at_t0_unchanged_when_future_perturbed"] = bool(a0.shape == b0.shape == (1, 3) and np.allclose(a0, b0))
    # ATR sans fuite pour un contact à hh:07
    res["lookahead_atr_10:07"] = lookahead_checks(df, "EURUSD", _ts("2025-09-03 10:07"))
    # simulation + stress
    tr = simulate_trades({"EURUSD": f}, select(c))
    res["sim_trades"] = int(len(tr))
    res["stress_le_sim"] = bool(len(tr) and (tr["r_stress"] <= tr["r"] + 1e-12).all())
    res["exit_le_30min"] = bool(len(tr) and (tr["minutes"] <= 30).all())
    res["pass"] = all(v is True or (isinstance(v, dict) and v.get("pass") is True)
                      for k, v in res.items() if k not in ("signals_found", "sim_trades"))
    return res


if __name__ == "__main__":
    import json
    r = run_all()
    print(json.dumps(r, indent=1, default=str))
    sys.exit(0 if r["pass"] else 1)
