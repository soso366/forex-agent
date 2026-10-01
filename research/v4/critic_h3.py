"""Critique de H3 (fade du fix de Londres) : robustesse, coûts, concentration. Aucune sélection ici :
la variante reste k = 0,5 · stop 1,5 ATR · 30 min · entrée 16:01 Londres."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import PAIRS, PIP
from .engine import build_ctx, run, signals_frame, stats

INF = np.inf


def fix_signals(ctx, k=0.5, stop=1.5, delay=1, month_end=None, target_r=None):
    b = ctx.m5
    loc = b.index.tz_convert("Europe/London")
    mins = loc.hour * 60 + loc.minute
    idx = np.nonzero(mins == 15 * 60 + 55)[0]
    c, o, a = b["c"].to_numpy(), b["o"].to_numpy(), b["atr"].to_numpy()
    me = (b.index.normalize().tz_localize(None) == b.index.normalize().tz_localize(None) + pd.offsets.BMonthEnd(0))
    rows = []
    for i in idx:
        if i < 6 or not np.isfinite(a[i]):
            continue
        if month_end is not None and bool(me[i]) != month_end:
            continue
        mv = c[i] - o[i - 5]
        if abs(mv) < k * a[i]:
            continue
        sd = stop * a[i]
        rows.append((i, int(-np.sign(mv)), sd, target_r * sd if target_r else INF))
    if not rows:
        return signals_frame(ctx, [], [], [], [])
    i, d, sd, td = map(np.array, zip(*rows))
    return signals_frame(ctx, i, d, sd, td, entry_times=b.index[i] + pd.Timedelta(minutes=5 + delay))


def go(C, hold=30, extra_pips=0.0, **kw):
    t = run(C, pd.concat([fix_signals(C[s], **kw) for s in PAIRS]), hold=hold)
    if extra_pips:
        t["r"] = t["r"] - 2 * extra_pips * t["sym"].map(PIP) / t["stop"]       # coût aller-retour supplémentaire
    return t


RES = []


def line(name, t):
    s = stats(t["r"])
    per = {p: stats(t[t["period"] == p]["r"])["exp"] for p in ("T1", "T2", "V1", "V2")}
    RES.append({"name": name, **s, **per})
    q = " ".join(f"{p}={per[p]:+.3f}" for p in per)
    return f"{name:<38} n={s['n']:4} exp={s['exp']:+.3f} t={s['t']:+.2f} pf={s['pf']:.2f} dd={s['dd']:.1f}R  {q}"


def main():
    C = {s: build_ctx(s) for s in PAIRS}
    base = go(C)
    print(line("RÉFÉRENCE k=0,5 stop 1,5 ATR 30 min", base))
    print("\n-- Voisins de paramètres")
    for k in (0.25, 0.75, 1.0):
        print(line(f"k={k}", go(C, k=k)))
    for st in (1.0, 2.0, 3.0):
        print(line(f"stop {st} ATR", go(C, stop=st)))
    for h in (10, 15, 20, 25):
        print(line(f"durée {h} min", go(C, hold=h)))
    print(line("cible 1 R", go(C, target_r=1.0)))
    print("\n-- Exécution")
    for dl in (0, 2, 3, 5):
        print(line(f"entrée retardée +{dl} min", go(C, delay=dl)))
    for x in (0.2, 0.5, 1.0):
        print(line(f"coût extra {x} pip par côté", go(C, extra_pips=x)))
    print("\n-- Concentration")
    print(line("sans fin de mois", go(C, month_end=False)))
    print(line("fin de mois seulement", go(C, month_end=True)))
    for d, g in base.groupby("dir"):
        print(line("achats" if d > 0 else "ventes", g))
    base["wd"] = pd.DatetimeIndex(base["time"]).tz_convert("Europe/London").day_name()
    for d, g in base.groupby("wd"):
        print(line(d, g))
    for s, g in base.groupby("sym"):
        print(line(s, g))
    for col in ("regime", "vol"):
        for k, g in base.groupby(col):
            print(line(f"{col}={k}", g))
    sp = []
    for s in PAIRS:
        m1 = C[s].m1
        loc = m1.index.tz_convert("Europe/London")
        at = (loc.hour == 16) & (loc.minute == 1)
        norm = (loc.hour == 14) & (loc.minute == 1)
        sp.append((s, m1["spread"][at].median() / PIP[s], m1["spread"][norm].median() / PIP[s]))
    print("\nSpread médian (pips) à 16:01 vs 14:01 Londres :", [(s, round(a, 2), round(b, 2)) for s, a, b in sp])
    r = base["r"].to_numpy()
    rng = np.random.default_rng(1)
    boots = np.array([rng.choice(r, len(r)).mean() for _ in range(5000)])
    print(f"Bootstrap espérance : IC90 = [{np.quantile(boots, .05):+.3f} ; {np.quantile(boots, .95):+.3f}] ; "
          f"P(≤0) = {(boots <= 0).mean():.4f}")
    import json
    (__import__("pathlib").Path(__file__).parent / "out" / "critic_h3.json").write_text(json.dumps(
        {"rows": RES, "boot": [float(np.quantile(boots, .05)), float(np.quantile(boots, .95))],
         "spread": [(s, float(a), float(b)) for s, a, b in sp]}, indent=1, default=float))
    base.to_pickle(__import__("pathlib").Path(__file__).parent / "out" / "h3_trades.pkl")


if __name__ == "__main__":
    main()
