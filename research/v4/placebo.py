"""Test placebo de H3 sur Train uniquement : la même règle de fade à chaque demi-heure de 08:00 à 20:30 (Londres)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import PAIRS
from .engine import TRAIN, build_ctx, run, signals_frame, stats


def fade_at(ctx, hh, mm, k=0.5):
    b = ctx.m5
    loc = b.index.tz_convert("Europe/London")
    mins = loc.hour * 60 + loc.minute
    idx = np.nonzero(mins == hh * 60 + mm - 5)[0]
    c, o, a = b["c"].to_numpy(), b["o"].to_numpy(), b["atr"].to_numpy()
    rows = []
    for i in idx:
        if i < 6 or not np.isfinite(a[i]):
            continue
        mv = c[i] - o[i - 5]
        if abs(mv) >= k * a[i]:
            rows.append((i, int(-np.sign(mv)), 1.5 * a[i]))
    if not rows:
        return signals_frame(ctx, [], [], [], [])
    i, d, sd = map(np.array, zip(*rows))
    return signals_frame(ctx, i, d, sd, np.full(len(i), np.inf), entry_times=b.index[i] + pd.Timedelta(minutes=6))


def main():
    C = {s: build_ctx(s) for s in PAIRS}
    out = []
    for hh in range(8, 21):
        for mm in (0, 30):
            t = run(C, pd.concat([fade_at(C[s], hh, mm) for s in PAIRS]))
            t = t[t["period"].isin(TRAIN)]
            s = stats(t["r"])
            out.append({"time": f"{hh:02d}:{mm:02d}", "n": s["n"], "exp": s["exp"], "t": s["t"],
                        **{p: stats(t[t["period"] == p]["r"])["exp"] for p in TRAIN}})
    (Path(__file__).parent / "out" / "placebo.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
