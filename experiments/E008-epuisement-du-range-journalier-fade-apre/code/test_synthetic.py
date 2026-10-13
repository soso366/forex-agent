"""Tests synthetiques (aucune donnee reelle) : ADR20 sans jour courant, signal sans futur, DST (changement 26/10/2025)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e008 as E


def synth(seed=1, start="2025-09-15", days=60):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=days * 1440, freq="1min", tz="UTC")
    idx = idx[idx.weekday < 5]
    p = 1.1 + np.cumsum(rng.normal(0, 1e-4, len(idx)))
    df = pd.DataFrame({"bo": p - 1e-5, "bh": p + 1e-4 - 1e-5, "bl": p - 1e-4 - 1e-5, "bc": p - 1e-5,
                       "ao": p + 1e-5, "ah": p + 1e-4 + 1e-5, "al": p - 1e-4 + 1e-5, "ac": p + 1e-5}, index=idx)
    df["mid"] = (df["bc"] + df["ac"]) / 2
    df["spread"] = df["ac"] - df["bc"]
    return df


def build(df):
    return E.Pair(df, "EURUSD")


def test_no_lookahead():
    df = synth()
    P1 = build(df)
    day = pd.Timestamp("2025-10-21")
    e1 = P1.events(13, "2025-10-21", "2025-10-22")
    adr1 = P1.adr20(day)
    df2 = df.copy()
    cut = E.london_ts(day, 13) + pd.Timedelta(minutes=1)     # tout apres l'open de 13:00 modifie
    m = df2.index >= cut
    df2.loc[m, ["bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "mid"]] *= 1.05
    P2 = build(df2)
    e2 = P2.events(13, "2025-10-21", "2025-10-22")
    assert len(e1) == 1 and len(e2) == 1
    assert abs(e1["M"].iloc[0] - e2["M"].iloc[0]) < 1e-12, "M depend du futur"
    assert abs(adr1 - P2.adr20(day)) < 1e-12, "ADR20 depend du jour courant/futur"
    assert abs(e1["atr"].iloc[0] - e2["atr"].iloc[0]) < 1e-12


def test_adr_excludes_current_day():
    df = synth()
    day = pd.Timestamp("2025-10-21")
    a = build(df).adr20(day)
    df2 = df.copy()
    m = (df2.index >= E.london_ts(day, 0)) & (df2.index < E.london_ts(day + pd.Timedelta(days=1), 0))
    df2.loc[m, ["bh", "ah"]] += 0.05            # explose le range du jour courant
    assert abs(build(df2).adr20(day) - a) < 1e-12
    assert build(df2).day_range(day) > 0.04


def test_dst():
    df = synth(days=90)
    P = build(df)
    e = P.events(13, "2025-10-21", "2025-11-01")
    ts = e.set_index("day")["ts"]
    assert ts[pd.Timestamp("2025-10-24")].hour == 12     # BST : 13:00 Londres = 12:00 UTC
    assert ts[pd.Timestamp("2025-10-28")].hour == 13     # GMT : 13:00 Londres = 13:00 UTC
    t = E.sim_events(P, E.select(e, 0.0), 240)
    t = t[t["exit"] == "time"]
    end = (t["time"] + pd.to_timedelta(t["minutes"], unit="m"))
    exp = [E.london_ts(d, 17) for d in t["day"]]
    assert all(abs((a - b).total_seconds()) <= 60 for a, b in zip(end, exp)), "sortie != 17:00 Londres"
    assert end.dt.hour.max() < 21


if __name__ == "__main__":
    test_no_lookahead(); test_adr_excludes_current_day(); test_dst()
    print("OK")
