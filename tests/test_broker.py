import unittest
from datetime import timedelta

from helpers import T0, simple_provider, store_for, tmp_cfg

from forex_agent.broker.paper import PaperBroker


class PaperBrokerTest(unittest.TestCase):
    def make(self, **paths):
        cfg = tmp_cfg()
        store = store_for(cfg)
        return cfg, store, PaperBroker(store, simple_provider(**paths), cfg)

    def open_eur(self, broker, direction="BUY", stop=1.16900, target=1.17200):
        return broker.open("EURUSD", direction, 500, stop, target, 0.4, 19, "Test_v1", "test", "{}", T0)

    def test_buy_fills_at_ask_sell_at_bid(self):
        _, store, b = self.make()
        self.assertAlmostEqual(store.trade(self.open_eur(b))["entry"], 1.17010)
        self.assertAlmostEqual(store.trade(self.open_eur(b, "SELL", 1.171, 1.168))["entry"], 1.17000)

    def test_time_stop_at_30_minutes(self):
        _, store, b = self.make()
        tid = self.open_eur(b)
        b.sync(T0 + timedelta(minutes=25))
        self.assertEqual(store.trade(tid)["status"], "open")
        b.sync(T0 + timedelta(minutes=35))
        t = store.trade(tid)
        self.assertEqual(t["status"], "closed")
        self.assertEqual(t["duration_min"], 30.0)
        self.assertIn("TIME_STOP", t["exit_reason"])

    def test_stop_first_when_sl_and_tp_in_same_minute(self):
        # la minute T0+2 touche à la fois le stop (1.16900) et la cible (1.17200)
        start = T0 - timedelta(hours=1)
        path = [(1.17, 1.17, 1.17, 1.17)] * 62 + [(1.17, 1.1725, 1.1685, 1.17)]
        _, store, b = self.make(EURUSD=path)
        tid = self.open_eur(b)
        b.sync(T0 + timedelta(minutes=5))
        t = store.trade(tid)
        self.assertEqual(t["exit_price"], 1.16900)
        self.assertEqual(t["intrabar_ambiguous"], 1)
        self.assertLess(t["pnl_eur"], 0)

    def test_gap_through_stop_fills_worse(self):
        path = [(1.17, 1.17, 1.17, 1.17)] * 61 + [(1.1680, 1.1681, 1.1679, 1.1680)]
        _, store, b = self.make(EURUSD=path)
        tid = self.open_eur(b)
        b.sync(T0 + timedelta(minutes=5))
        self.assertAlmostEqual(store.trade(tid)["exit_price"], 1.1680)

    def test_pnl_converted_to_eur_and_balance_updated(self):
        path = [(1.17, 1.17, 1.17, 1.17)] * 61 + [(1.1719, 1.1722, 1.1718, 1.1721)]
        _, store, b = self.make(EURUSD=path)
        tid = self.open_eur(b)
        b.sync(T0 + timedelta(minutes=5))
        t = store.trade(tid)
        expected = (1.17200 - 1.17010) * 500 / 1.17195       # gain en USD converti en EUR (mid à la sortie)
        self.assertAlmostEqual(t["pnl_eur"], expected, places=3)
        self.assertAlmostEqual(b.balance, 50 + t["pnl_eur"], places=6)


if __name__ == "__main__":
    unittest.main()
