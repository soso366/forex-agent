"""Test synthétique E006 : dérive connue puis retour -> trade fade gagnant ; pas de look-ahead ; sortie < 21h.
Lancer : python3 test_synthetic.py"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e006 as E


def make(days=40, post_drift=-0.0020, seed=1, tweak_after=None):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-09-01", periods=days * 1440, freq="1min", tz="UTC")
    n = len(idx)
    step = rng.normal(0, 0.00004, n)
    h = idx.hour.values + idx.minute.values / 60
    for k in range(days):
        s = k * 1440
        step[s:s + 420] += 0.0030 / 420 * (1 if k % 2 == 0 else -1)          # dérive 00-07 : +30 pips / -30 pips
        step[s + 425:s + 665] += post_drift / 240 * (1 if k % 2 == 0 else -1)  # retour 07:05-11:05
    mid = 1.10 + np.cumsum(step)
    if tweak_after is not None:    # modifie TOUT ce qui suit la minute tweak_after du jour 30
        s = 30 * 1440 + tweak_after
        mid[s:] += 0.01
    sp = 0.00010
    df = pd.DataFrame(index=idx)
    df["bo"] = mid - sp / 2; df["ao"] = mid + sp / 2
    df["bc"] = np.r_[df["bo"].values[1:], df["bo"].values[-1]]; df["ac"] = df["bc"] + sp
    df["bh"] = np.maximum(df["bo"], df["bc"]) + 0.00002; df["ah"] = np.maximum(df["ao"], df["ac"]) + 0.00002
    df["bl"] = np.minimum(df["bo"], df["bc"]) - 0.00002; df["al"] = np.minimum(df["ao"], df["ac"]) - 0.00002
    df["mid"] = (df["bc"] + df["ac"]) / 2; df["spread"] = df["ac"] - df["bc"]
    return df


def run(df):
    P = E.Pair(df, "EURUSD")
    ev = P.events("main", "2025-09-16", "2025-10-11")
    sel = E.select(ev, 1.0, False)
    return P, ev, sel, E.sim_events(P, sel, 240, +1)


df = make()
P, ev, sel, t = run(df)
assert len(sel) >= 10, len(sel)
assert (t["dir"] == -np.sign(t["D"])).all(), "direction = opposé à la dérive"
assert t["r"].mean() > 0.3, t["r"].mean()                      # retour -20 pips pour stop 3 ATR : gain net positif
assert ((t["time"] + pd.to_timedelta(t["minutes"], unit="m")).dt.hour < 21).all()
assert (t["time"].dt.hour == 7).all() and (t["time"].dt.minute == 5).all()
tc = E.sim_events(P, sel, 240, -1)
assert tc["r"].mean() < -0.3, "la continuation doit perdre sur ce jeu"
# pas de look-ahead : modifier les données APRÈS 07:00 (jour 30) ne change ni z, ni dérive, ni décision
df2 = make(tweak_after=7 * 60 + 1)
_, ev2, sel2, _ = run(df2)
a = ev[ev["k"] == 30].iloc[0]; b = ev2[ev2["k"] == 30].iloc[0]
assert a["z"] == b["z"] and a["D"] == b["D"] and a["filt_ok"] == b["filt_ok"], "look-ahead sur z/filtre"
# placebo sans effet : retour nul -> espérance proche du coût (négative)
dfn = make(post_drift=0.0)
_, _, seln, tn = run(dfn)
assert tn["r"].mean() < 0.1, tn["r"].mean()
print("OK synthétique : n=%d, R fade=%.2f, R continuation=%.2f, R sans retour=%.2f"
      % (len(t), t["r"].mean(), tc["r"].mean(), tn["r"].mean()))
