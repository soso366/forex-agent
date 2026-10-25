"""Contrôles du moteur : pas d'avantage fictif sur marche aléatoire, pas de regard vers le futur."""
import unittest

import numpy as np
import pandas as pd

from dsim import Book, Costs, daily, hourly, summarize
from methods import METHODS


def walk(seed, start="2016-01-04", end="2019-12-31"):
    rng = np.random.default_rng(seed)
    t = pd.date_range(start, end, freq="min", tz="UTC")
    ny = t.tz_convert("America/New_York")
    t = t[(ny + pd.Timedelta(hours=7)).dayofweek < 5]
    b = 1.1 + np.cumsum(rng.normal(0, 1.5e-4, len(t)))
    return pd.DataFrame({"time": t, "bid_open": b, "bid_high": b, "bid_low": b, "bid_close": b,
                         "ask_open": b, "ask_high": b, "ask_low": b, "ask_close": b})


def trades(m1, name, costs=Costs("zero", 0, 0)):
    h = hourly(m1)
    d = daily(h)
    fn, p, _ = METHODS[name]
    bk = Book(costs)
    fn(h, d, 0, len(h), bk, p)
    return bk


class RandomWalk(unittest.TestCase):
    def test_no_fake_edge(self):
        m1 = walk(5)
        for name in METHODS:
            s = summarize(trades(m1, name), None, None)
            self.assertTrue(s["t_stat"] is None or abs(s["t_stat"]) < 2.6, (name, s["t_stat"]))


class NoLookAhead(unittest.TestCase):
    def test_future_change_does_not_change_past(self):
        m1 = walk(7, end="2017-12-31")
        cut = len(m1) * 3 // 4
        m1b = m1.copy()
        noise = np.cumsum(np.random.default_rng(1).normal(0, 3e-4, len(m1) - cut))
        for c in m1.columns[1:]:
            m1b.loc[cut:, c] = m1.loc[cut:, c].to_numpy() + noise
        cut_t = m1.time[cut].floor("1h")
        for name in METHODS:
            a = [(str(t["t_entry"]), t["side"]) for t in trades(m1, name).trades if t["t_entry"] < cut_t]
            b = [(str(t["t_entry"]), t["side"]) for t in trades(m1b, name).trades if t["t_entry"] < cut_t]
            self.assertEqual(a, b, name)


if __name__ == "__main__":
    unittest.main()
