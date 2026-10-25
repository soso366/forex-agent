"""Tests : aucune hypothèse ne regarde le futur ; le jour journalier utilisé est toujours clos."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "oss_eurusd"))
from engine import Costs, Sim, resample  # noqa: E402
from hypotheses import HYPOTHESES, daily_bars  # noqa: E402


def make_m1(n, seed):
    rng = np.random.default_rng(seed)
    bid = 1.1 + np.cumsum(rng.normal(0, 2.5e-4, n))
    t = pd.date_range("2025-01-06 00:00", periods=n, freq="min", tz="UTC")
    s = 0.00002
    return pd.DataFrame({"time": t, "bid_open": bid, "bid_high": bid + 1e-4, "bid_low": bid - 1e-4, "bid_close": bid,
                         "ask_open": bid + s, "ask_high": bid + 1e-4 + s, "ask_low": bid - 1e-4 + s, "ask_close": bid + s})


def trades(m1, name):
    prep_fn, fn, _, default = HYPOTHESES[name]
    cache = {tf: resample(m1, tf) for tf in ("1h", "4h", "15min")}
    cache["daily"] = daily_bars(m1)
    prep = prep_fn(m1, cache)
    bars = prep[0] if isinstance(prep, tuple) else prep
    sim = Sim(m1, Costs("x", 7, 0.2), 10_000, i_end=len(m1))
    fn(sim, prep, 2, len(bars), default)
    return [(str(t["t_entry"]), t["side"]) for t in sim.trades]


class NoLookAhead(unittest.TestCase):
    def test_future_change_does_not_change_past(self):
        m1 = make_m1(60 * 24 * 90, 3)
        cut = len(m1) * 2 // 3
        m1b = m1.copy()
        noise = np.random.default_rng(9).normal(0, 4e-3, len(m1) - cut)
        for c in m1.columns[1:]:
            m1b.loc[cut:, c] = m1.loc[cut:, c].to_numpy() + noise
        cut_t = str(m1.time[cut])
        for name in HYPOTHESES:
            a = [x for x in trades(m1, name) if x[0] < cut_t]
            b = [x for x in trades(m1b, name) if x[0] < cut_t]
            self.assertGreater(len(a), 0, name)
            self.assertEqual(a, b, name)

    def test_daily_day_closes_at_17h_new_york(self):
        m1 = make_m1(60 * 24 * 3, 1)
        d = daily_bars(m1)
        # 06/01/2025 (hiver) : 17 h New York = 22 h UTC → la minute 22:00 UTC appartient au jour suivant
        self.assertEqual(len(d), 4)


if __name__ == "__main__":
    unittest.main()
