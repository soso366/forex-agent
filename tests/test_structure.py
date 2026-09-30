import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from helpers import T0, UTC, setup, simple_provider, store_for, tmp_cfg

from forex_agent.analysis import structure as st
from forex_agent.broker.paper import PaperBroker
from forex_agent.risk.manager import RiskManager
from forex_agent.strategies.base import qualifies


def bars(closes, spread_wick=0.0002, start=T0):
    c = np.array(closes, dtype=float)
    o = np.concatenate([[c[0]], c[:-1]])
    idx = pd.date_range(start, periods=len(c), freq="15min", tz="UTC")
    return pd.DataFrame({"o": o, "h": np.maximum(o, c) + spread_wick, "l": np.minimum(o, c) - spread_wick, "c": c},
                        index=idx)


def zigzag(points, steps=4):
    out = []
    for a, b in zip(points, points[1:]):
        out += list(np.linspace(a, b, steps, endpoint=False))
    return out + [points[-1]]


class StructureTest(unittest.TestCase):
    def test_uptrend_holds_until_protected_low_closed(self):
        up = zigzag([1.10, 1.12, 1.11, 1.13, 1.12, 1.14, 1.13, 1.15])
        s = st.structure_trend(bars(up))
        self.assertEqual(s.trend, "up")
        self.assertGreaterEqual(s.bos_count, 2)
        broken = up + zigzag([1.15, 1.10], steps=8)[1:]
        self.assertEqual(st.structure_trend(bars(broken)).trend, "down")

    def test_objective_candle_triggers(self):
        prev = pd.Series({"o": 1.1010, "h": 1.1012, "l": 1.0998, "c": 1.1000})       # rouge
        engulf = pd.Series({"o": 1.0999, "h": 1.1016, "l": 1.0997, "c": 1.1014})
        self.assertEqual(st.candle_trigger(engulf, prev, 1), "engulfing")
        prev_green = pd.Series({"o": 1.1000, "h": 1.1010, "l": 1.0998, "c": 1.1008})
        above = pd.Series({"o": 1.1008, "h": 1.1016, "l": 1.1006, "c": 1.1012})
        self.assertEqual(st.candle_trigger(above, prev_green, 1), "close_above")
        hammer = pd.Series({"o": 1.1007, "h": 1.1010, "l": 1.0990, "c": 1.1009})    # corps au-dessus de 38,2 %
        self.assertEqual(st.candle_trigger(hammer, prev_green, 1), "candle_38.2")
        doji = pd.Series({"o": 1.1000, "h": 1.1010, "l": 1.0990, "c": 1.1001})
        self.assertIsNone(st.candle_trigger(doji, prev_green, 1))

    def test_fvg_detection(self):
        df = pd.DataFrame({"h": [1.10, 1.105, 1.112], "l": [1.095, 1.099, 1.102]})
        self.assertEqual(st.fvgs(df, 0, 1), [(2, 1.10, 1.102)])
        self.assertEqual(st.fvgs(df, 0, -1), [])


class TimeTest(unittest.TestCase):
    def test_forex_day_closes_at_5pm_new_york(self):
        self.assertEqual(st.forex_day(pd.Timestamp("2026-09-09 20:59", tz="UTC")).day, 9)
        self.assertEqual(st.forex_day(pd.Timestamp("2026-09-09 21:00", tz="UTC")).day, 10)
        self.assertEqual(st.forex_day(pd.Timestamp("2026-12-09 21:59", tz="UTC")).day, 9)    # hiver : 22:00 UTC

    def test_killzones_follow_new_york_dst(self):
        zones = {"london": [2, 5], "new_york_am": [7, 10]}
        self.assertEqual(st.killzone(datetime(2026, 9, 9, 7, 0, tzinfo=UTC), zones), "london")      # 03:00 NY
        self.assertEqual(st.killzone(datetime(2026, 12, 9, 7, 0, tzinfo=UTC), zones), "london")     # 02:00 NY
        self.assertIsNone(st.killzone(datetime(2026, 12, 9, 6, 30, tzinfo=UTC), zones))
        self.assertEqual(st.killzone(datetime(2026, 9, 9, 12, 0, tzinfo=UTC), zones), "new_york_am")

    def test_nfp_blackout(self):
        cfg = tmp_cfg()
        nfp = datetime(2026, 10, 2, 12, 30, tzinfo=UTC)                  # 1er vendredi, 8:30 NY
        self.assertTrue(st.news_blackout(nfp + timedelta(minutes=10), "EURUSD", cfg)[0])
        self.assertFalse(st.news_blackout(nfp + timedelta(hours=2), "EURUSD", cfg)[0])
        self.assertFalse(st.news_blackout(nfp, "EURGBP", cfg)[0])      # pas d'USD dans la paire
        cfg["news"]["events"] = [{"time": "2026-10-28T18:00Z", "name": "FOMC", "currencies": ["USD"]}]
        self.assertTrue(st.news_blackout(datetime(2026, 10, 28, 17, 45, tzinfo=UTC), "USDJPY", cfg)[0])

    def test_previous_day_liquidity(self):
        idx = pd.date_range("2026-09-08 00:00", "2026-09-09 10:00", freq="h", tz="UTC")
        h1 = pd.DataFrame({"o": 1.1, "h": 1.101, "l": 1.099, "c": 1.1}, index=idx)
        h1.loc["2026-09-08 15:00", "h"] = 1.1050                         # jour Forex du 8 (21:00 UTC la veille → 21:00)
        h1.loc["2026-09-08 22:00", "h"] = 1.1080                         # appartient déjà au jour du 9
        m15 = h1.resample("15min").ffill()
        pools = st.liquidity_pools(h1, m15, datetime(2026, 9, 9, 10, 0, tzinfo=UTC), 0.001)
        pdh = next(p for p in pools if p["name"] == "PDH")
        self.assertAlmostEqual(pdh["price"], 1.1050)


class RulesTest(unittest.TestCase):
    def test_entry_is_binary(self):
        s = setup()
        s.essential = ["context", "trigger", "rr"]
        s.confirmations = {"context": True, "trigger": False, "rr": True, "killzone": True}
        ok, why = qualifies(s, {"min_optional_confirmations": 0})
        self.assertFalse(ok)
        self.assertIn("trigger", why)
        s.confirmations["trigger"] = True
        self.assertTrue(qualifies(s, {"min_optional_confirmations": 0})[0])

    def test_no_reentry_after_loss_on_same_pair(self):
        cfg = tmp_cfg()
        store = store_for(cfg)
        t = T0 - timedelta(minutes=10)
        store.insert_trade(symbol="EURUSD", direction="BUY", strategy="T", entry=1, stop=0.99, initial_stop=0.99,
                           target=1.02, units=1, risk_eur=0.5, entry_time=t.isoformat(), exit_time=t.isoformat(),
                           pnl_eur=-0.4, status="closed")
        rm = RiskManager(cfg, store)
        v = rm.evaluate(setup(stop=1.16910), 1.17, 1.1701, [], 49.6, 49.6,
                        {"EURUSD": 1.17005, "GBPUSD": 1.34, "USDJPY": 148.0}, T0)
        self.assertFalse(v.approved)
        self.assertIn("ré-entrée", v.reasons[0])

    def test_mfe_mae_and_r_multiple_recorded(self):
        path = [(1.17, 1.17, 1.17, 1.17)] * 60 + [(1.17, 1.1705, 1.1696, 1.1700)] + [(1.1700, 1.1721, 1.1699, 1.1719)]
        cfg = tmp_cfg()
        store = store_for(cfg)
        b = PaperBroker(store, simple_provider(EURUSD=path), cfg)
        tid = b.open("EURUSD", "BUY", 500, 1.16910, 1.17200, 0.4, 19, "Test", "t", "{}", T0)
        b.sync(T0 + timedelta(minutes=5))
        tr = store.trade(tid)
        self.assertEqual(tr["status"], "closed")
        self.assertAlmostEqual(tr["r_multiple"], (1.17200 - 1.17010) / (1.17010 - 1.16910), places=2)
        self.assertGreater(tr["mae_r"], 0.1)
        self.assertGreaterEqual(tr["mfe_r"], tr["r_multiple"] - 1e-9)


if __name__ == "__main__":
    unittest.main()
