"""Tests automatiques du banc de test OSS EUR/USD (python -m unittest test_oss_eurusd)."""
import unittest

import numpy as np
import pandas as pd

from engine import (Costs, Sim, atr_mt5, bands_mt5, normalize_lot_clamp, normalize_lot_floor,
                    resample, rsi_mt5, server_hour)
from strategies import run_sbrakni, run_smizxe


def make_m1(bid, spread=0.00002, start="2025-01-06 00:00"):
    bid = np.asarray(bid, float)
    t = pd.date_range(start, periods=len(bid), freq="min", tz="UTC")
    return pd.DataFrame({
        "time": t, "bid_open": bid, "bid_high": bid + 0.00005, "bid_low": bid - 0.00005, "bid_close": bid,
        "ask_open": bid + spread, "ask_high": bid + 0.00005 + spread,
        "ask_low": bid - 0.00005 + spread, "ask_close": bid + spread,
    })


class Indicators(unittest.TestCase):
    def test_rsi_extremes(self):
        up = np.arange(30, dtype=float)
        self.assertEqual(rsi_mt5(up, 14)[-1], 100.0)
        self.assertEqual(rsi_mt5(up[::-1].copy(), 14)[-1], 0.0)
        self.assertTrue(np.isnan(rsi_mt5(up, 14)[13]))

    def test_rsi_wilder(self):
        rng = np.random.default_rng(1)
        c = 1.1 + np.cumsum(rng.normal(0, 1e-4, 300))
        d = np.diff(c)
        g, l = np.clip(d, 0, None), np.clip(-d, 0, None)
        ag, al = g[:14].mean(), l[:14].mean()
        for i in range(14, len(d)):
            ag, al = (ag * 13 + g[i]) / 14, (al * 13 + l[i]) / 14
        self.assertAlmostEqual(rsi_mt5(c, 14)[-1], 100 - 100 / (1 + ag / al), places=9)

    def test_bands_population_std(self):
        c = np.array([1, 2, 3, 4, 5], float)
        u, m, lo = bands_mt5(c, 5, 2.0)
        self.assertAlmostEqual(m[-1], 3.0)
        self.assertAlmostEqual(u[-1] - m[-1], 2 * np.sqrt(2.0))

    def test_atr_sma(self):
        h = np.array([2, 3, 4, 5], float); lo = h - 1; c = h - 0.5
        a = atr_mt5(h, lo, c, 2)
        self.assertTrue(np.isnan(a[1]))
        self.assertAlmostEqual(a[3], 1.5)

    def test_server_hour(self):
        t = pd.Series(pd.to_datetime(["2025-01-15 12:00", "2025-07-15 12:00"], utc=True))
        self.assertEqual(list(server_hour(t, "eet_ny")), [14, 15])


class Simulation(unittest.TestCase):
    def test_stop_first_when_ambiguous(self):
        m1 = make_m1([1.1] * 5)
        m1.loc[2, ["bid_high", "bid_low"]] = [1.1020, 1.0980]
        sim = Sim(m1, Costs("x", 0, 0), 10_000, i_end=5)
        sim.open(1, 0, 1.10002, 1.0990, 1.1010, 1.0)
        sim.advance_to(5)
        self.assertEqual(sim.trades[0]["reason"], "stop")
        self.assertEqual(sim.ambiguous, 1)

    def test_buy_at_ask_exit_at_bid_with_costs(self):
        m1 = make_m1([1.1, 1.1, 1.1020, 1.1020], spread=0.0001)
        sim = Sim(m1, Costs("x", 7.0, 0.2), 10_000, i_end=4)
        sim.open(1, 0, m1.ask_open[0], 1.09, 1.1010, 1.0)
        sim.advance_to(4)
        t = sim.trades[0]
        self.assertAlmostEqual(t["entry"], 1.1001 + 0.00002)
        self.assertEqual(t["reason"], "objectif_gap")
        self.assertAlmostEqual(t["pnl"], (1.1020 - 1.10012) * 100_000 - 7.0, places=6)

    def test_lots(self):
        self.assertEqual(normalize_lot_floor(100 / 300), 0.33)
        self.assertEqual(normalize_lot_floor(1.5 / 300), 0.0)
        self.assertEqual(normalize_lot_clamp(0.004), 0.01)


class NoLookAhead(unittest.TestCase):
    """Changer le futur ne doit jamais changer les décisions passées."""

    def _trades(self, fn, m1, tf):
        bars = resample(m1, tf)
        sim = Sim(m1, Costs("x", 7, 0.2), 10_000, i_end=len(m1))
        fn(m1, bars, 2, len(bars), sim)
        return [(str(t["t_entry"]), t["side"]) for t in sim.trades]

    def test_strategies(self):
        rng = np.random.default_rng(7)
        bid = 1.1 + np.cumsum(rng.normal(0, 3e-4, 60 * 24 * 20))
        m1 = make_m1(bid)
        cut = len(m1) * 3 // 4
        m1b = m1.copy()
        noise = rng.normal(0, 5e-3, len(m1) - cut)
        for c in m1.columns[1:]:
            m1b.loc[cut:, c] = m1.loc[cut:, c].to_numpy() + noise
        cut_t = str(m1.time[cut])
        for fn, tf in ((lambda *a: run_smizxe(*a, "reversal"), "1h"),
                       (lambda *a: run_smizxe(*a, "level"), "1h"),
                       (lambda *a: run_sbrakni(*a, "utc"), "5min")):
            a = [x for x in self._trades(fn, m1, tf) if x[0] < cut_t]
            b = [x for x in self._trades(fn, m1b, tf) if x[0] < cut_t]
            self.assertGreater(len(a), 0)
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
