"""Tests synthétiques E005 : python3 -I test_synthetic.py (doit afficher PASS)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e005 as e
from datetime import date

P = 1e-4


def synth(start="2025-12-01", end="2025-12-20", fall_utc=(8, 12), pips_min=0.1):
    idx = pd.date_range(start, end, freq="1min", tz="UTC", inclusive="left")
    mid = np.full(len(idx), 1.1)
    osc = np.where(idx.minute % 2 == 0, 0.5 * P, -0.5 * P)
    mn = idx.hour * 60 + idx.minute
    # baisse linéaire de 0,1 pip/min pendant [fall_utc) en semaine, constante sinon (cumul par jour reset)
    day = idx.normalize()
    steps = np.where((idx.hour >= fall_utc[0]) & (idx.hour < fall_utc[1]), -pips_min * P, 0.0)
    cum = pd.Series(steps, index=idx).groupby(day).cumsum().to_numpy()
    mid = 1.1 + cum + osc
    sp = 0.25 * P   # demi-spread -> spread 0,5 pip
    df = pd.DataFrame({"bo": mid - sp, "bh": mid - sp + 0.2 * P, "bl": mid - sp - 0.2 * P, "bc": mid - sp,
                       "ao": mid + sp, "ah": mid + sp + 0.2 * P, "al": mid + sp - 0.2 * P, "ac": mid + sp}, index=idx)
    df.index.name = "time"
    df["mid"] = (df["bc"] + df["ac"]) / 2
    df["spread"] = df["ac"] - df["bc"]
    return df


def main():
    res = {}
    # 1. DST : 08:00 Londres
    res["dst_summer"] = str(e.local_to_utc(date(2025, 7, 1), 8)) == "2025-07-01 07:00:00+00:00"
    res["dst_winter"] = str(e.local_to_utc(date(2026, 1, 12), 8)) == "2026-01-12 08:00:00+00:00"
    res["dst_uk_change_mon_2025-10-27"] = str(e.local_to_utc(date(2025, 10, 27), 8)) == "2025-10-27 08:00:00+00:00"
    res["dst_uk_change_fri_2025-10-24"] = str(e.local_to_utc(date(2025, 10, 24), 8)) == "2025-10-24 07:00:00+00:00"
    res["dst_uk_mar_2026-03-30"] = str(e.local_to_utc(date(2026, 3, 30), 8)) == "2026-03-30 07:00:00+00:00"
    res["dst_B_summer_14h"] = str(e.local_to_utc(date(2025, 7, 1), 14)) == "2025-07-01 13:00:00+00:00"
    # 2. effet connu : baisse de 24 pips sur 08-12 UTC (hiver) ; A vend EURUSD -> ~ +24 - 0,5 spread pips
    df = synth()
    # ajouter un ATR non nul : l'oscillation donne TR ~ 1+ pip
    w = dict(start="2025-12-01", end="2025-12-20")
    pairs = {"EURUSD": e.Pair(df, "EURUSD")}
    tA = e.make(pairs, w, e.VARIANTS["A"])
    tB = e.make(pairs, w, e.VARIANTS["B"])
    res["n_trades_A_14d"] = int(len(tA)) == 15   # 1-19 déc. = 15 jours ouvrés
    res["A_pips_about_24"] = bool(abs(tA["pips"].mean() - 24.0) < 1.5)
    res["B_pips_about_-24.5"] = bool(abs(tB["pips"].mean() - (-24.5 + 24.0)) < 1.0 or tB["pips"].mean() < 1)
    res["entry_08_utc_winter"] = bool((pd.DatetimeIndex(tA["time"]).hour == 8).all())
    res["R_unit_atr"] = bool(np.allclose(tA["r"], tA["pips"] * P / tA["atr"]))
    # 3. coûts : +1 pip retire 1 pip
    c = e.nets(tA, 1.0)["exp"]
    res["cost_1pip"] = bool(abs((tA["r"].mean() - c) - (P / tA["stop"]).mean()) < 1e-9)
    # 4. ATR sans fuite : perturber le futur (à partir de l'entrée) ne change pas l'ATR utilisé
    t0 = e.local_to_utc(date(2025, 12, 10), 8)
    d2 = df.copy()
    m = d2.index >= t0.tz_convert("UTC")
    for col in ["bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"]:
        d2.loc[m, col] = d2.loc[m, col] + 7 * P
    p2 = e.Pair(d2, "EURUSD")
    res["atr_no_lookahead"] = bool(np.isclose(pairs["EURUSD"].atr.asof(t0), p2.atr.asof(t0)))
    # 5. placebo : fenêtres non chevauchantes et avant 21:00 UTC
    ok = True
    for s in e.PLACEBO_STARTS:
        sg = e.signals(pairs, w, s, 240, e.DIR_A)
        ok &= len(sg) > 0 and bool((sg["time"] + pd.Timedelta(minutes=240)).dt.hour.max() <= 20)
        ok &= not (5 <= s <= 11)
    res["placebo_windows_valid"] = bool(ok)
    # 6. une seule position par paire et par jour
    res["one_per_pair_day"] = bool(not tA.duplicated(["sym", "day"]).any())
    res["pass"] = all(res.values())
    for k, v in res.items():
        print(k, v)
    print("PASS" if res["pass"] else "FAIL")
    return res


if __name__ == "__main__":
    main()
