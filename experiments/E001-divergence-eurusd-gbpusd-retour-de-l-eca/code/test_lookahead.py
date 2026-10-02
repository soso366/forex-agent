"""Test de non-look-ahead (exigé par le CRITIC) : perturber le futur ne doit rien changer au présent."""
from __future__ import annotations

import numpy as np
import pandas as pd

from e001 import PAIRS, TZ, Features

COLS = ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")


def _perturb(raw: dict, t0: pd.Timestamp, strict_after: bool, seed: int = 3) -> dict:
    rng = np.random.default_rng(seed)
    out = {}
    for s in PAIRS:
        df = raw[s].copy()
        m = (df.index > t0) if strict_after else (df.index >= t0)
        noise = rng.normal(0, 0.003, m.sum())
        for c in COLS:
            df.loc[m, c] = df.loc[m, c].to_numpy() * (1 + noise)
        df.loc[m, "ac"] += rng.uniform(0, 0.0005, m.sum())   # spreads futurs modifiés aussi
        df["mid"] = (df["bc"] + df["ac"]) / 2
        df["spread"] = df["ac"] - df["bc"]
        out[s] = df
    return out


def run(raw: dict, W: int = 15) -> dict:
    base = Features(raw, W)
    J = base.valid_days[25]
    j0 = pd.Timestamp(J).tz_localize(TZ).tz_convert("UTC")
    pert = Features(_perturb(raw, j0, strict_after=False), W)
    res = {"day": str(pd.Timestamp(J).date()), "W": W}
    res["sigma_x_unchanged"] = bool(np.isclose(base.sx[J], pert.sx[J], rtol=0, atol=0))
    res["sigma_u_unchanged"] = bool(np.isclose(base.su[J], pert.su[J], rtol=0, atol=0))
    res["spread_median_unchanged"] = all(base.med[s][J] == pert.med[s][J] for s in PAIRS)
    before = base.grid[base.grid < j0]
    res["atr_before_J_unchanged"] = all(np.allclose(base.atr[s].reindex(before), pert.atr[s].reindex(before),
                                                    equal_nan=True) for s in PAIRS)
    # minute de scan t0 du jour J : perturber strictement après t0 ne change pas les features à t0
    fb = base.frame()
    t0 = fb[fb["day"] == J].index[40]
    fp = Features(_perturb(raw, t0, strict_after=True), W).frame()
    cols = ["z", "uz", "d_EURUSD", "d_GBPUSD", "atrsig_EURUSD", "atrsig_GBPUSD", "spok", "fautive"]
    res["scan_t0"] = str(t0)
    res["features_at_t0_unchanged"] = bool(all(
        (fb.at[t0, c] == fp.at[t0, c]) or (pd.isna(fb.at[t0, c]) and pd.isna(fp.at[t0, c])) for c in cols))
    res["sanity_future_changed"] = bool(base.sx.get(base.valid_days[-1], np.nan) != pert.sx.get(base.valid_days[-1], np.nan))
    res["pass"] = all(v for k, v in res.items() if k.endswith("unchanged")) and res["sanity_future_changed"]
    return res
