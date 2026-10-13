"""Tests synthetiques anti-look-ahead : z(t), sigma, ATR ne dependent pas des prix posterieurs a la cloture de la barre ;
sigma strictement passe ; DST ; sortie <= 17:00 Londres et < 21:00 UTC."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e009 as E

COLS = ["bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "mid"]


def synth(seed, start="2025-09-01", days=40, scale=1.0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=days * 1440, freq="1min", tz="UTC")
    idx = idx[idx.weekday < 5]
    p = scale + np.cumsum(rng.normal(0, 1e-4 * scale, len(idx)))
    h = 1e-4 * scale
    df = pd.DataFrame({"bo": p - h / 10, "bh": p + h - h / 10, "bl": p - h - h / 10, "bc": p - h / 10,
                       "ao": p + h / 10, "ah": p + h + h / 10, "al": p - h + h / 10, "ac": p + h / 10}, index=idx)
    df["mid"] = (df["bc"] + df["ac"]) / 2
    df["spread"] = df["ac"] - df["bc"]
    return df


def raw(mod=None):
    r = {"USDJPY": synth(1, scale=100.0), "EURUSD": synth(2), "GBPUSD": synth(3)}
    if mod:
        for k in r:
            mod(r[k])
    return r


def test_no_lookahead():
    D1 = E.Data(raw())
    L = pd.Timestamp("2025-09-24 10:00", tz="UTC")           # barre M5 [10:00, 10:05), cloture 10:05
    assert L in D1.z.index
    cut = L + pd.Timedelta(minutes=5)

    def mod(df):
        m = df.index >= cut
        df.loc[m, COLS] *= 1.05
    D2 = E.Data(raw(mod))
    for name in ("z", "g"):
        a, b = getattr(D1, name), getattr(D2, name)
        assert abs(a[L] - b[L]) < 1e-12, f"{name}(t) depend du futur"
    assert abs(D1.atr[L] - D2.atr[L]) < 1e-12
    # sigma strictement passe : modifier la valeur de g a L ne change pas sigma a L (z recalcule avec g[L] fausse)
    g = D1.g.copy()
    g2 = g.copy()
    g2[L] = g[L] * 10
    z1, z2 = E.zscore(g), E.zscore(g2)
    assert abs(z1[L] * 1 - z2[L] / 10) < 1e-9, "sigma(L) contient g(L)"
    # ... et l'observation suivante utilise bien g(L) (decale de 1)
    nxt = z1.index[z1.index.get_loc(L) + 1]
    assert abs(z1[nxt] - z2[nxt]) > 1e-6


def test_signal_entry_after_close_and_exit():
    D = E.Data(raw())
    ev = E.build_events(D.z, D.atr, 1.0, 120)
    assert len(ev) > 0
    lt = ev["ts"].dt.tz_convert(E.LONDON)
    assert ((lt.dt.hour * 60 + lt.dt.minute) >= 8 * 60).all() and (lt.dt.hour < 15).all()
    assert (ev.groupby("day").size() <= 2).all()
    gaps = ev["ts"].diff().dropna()
    assert (gaps[ev["day"].diff().dropna() == pd.Timedelta(0)] >= pd.Timedelta(minutes=120)).all()
    assert ((ev["ts"].dt.minute % 5) == 0).all()
    t = E.sim_events(D, ev)
    end = t["time"] + pd.to_timedelta(t["minutes"], unit="m")
    assert end.dt.hour.max() < 21
    assert all(e <= E.london_ts(d, 17) + pd.Timedelta(minutes=1) for e, d in zip(end, t["day"]))


def test_dst():
    D = E.Data(raw())
    ev = E.build_events(D.z, D.atr, 0.5, 120)
    s = ev[ev["day"] == pd.Timestamp("2025-09-24")]
    assert len(s) and (s["ts"].dt.tz_convert(E.LONDON).dt.hour >= 8).all()
    assert E.london_ts("2025-10-24", 17).hour == 16 and E.london_ts("2025-10-28", 17).hour == 17


def test_pipeline_synthetic():
    """Fait tourner evaluate() sur donnees synthetiques (aucune donnee reelle) pour exclure un bug avant verrouillage."""
    import tempfile, run
    D = E.Data(raw())
    run.RES = Path(tempfile.mkdtemp())
    run.SPLITS_BAK = E.SPLITS["train"]
    E.SPLITS["train"] = ("2025-09-01", "2025-10-15")
    res = run.evaluate(D, "train", n_perm=5)
    c = run.judge_train(res)
    assert isinstance(c, dict) and "6_without_announce_gt_0" in c
    print("pipeline OK", res["A"]["stats"]["n"])


if __name__ == "__main__":
    test_no_lookahead(); test_signal_entry_after_close_and_exit(); test_dst(); test_pipeline_synthetic()
    print("OK")
