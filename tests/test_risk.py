import unittest
from datetime import timedelta

from helpers import MIDS, T0, setup, store_for, tmp_cfg

from forex_agent.risk.manager import RiskManager

BID, ASK = 1.17000, 1.17010
QUOTES = {"EURUSD": (1.17000, 1.17010), "GBPUSD": (1.34000, 1.34012), "USDJPY": (148.000, 148.010)}


def trade_row(symbol="EURUSD", direction="BUY", entry=1.17010, stop=1.16910, units=585, margin=19.5):
    return {"id": 1, "symbol": symbol, "direction": direction, "entry": entry, "stop": stop,
            "units": units, "margin_eur": margin}


class RiskSizingTest(unittest.TestCase):
    def verdict(self, capital, s=None, open_trades=(), cfg=None):
        cfg = cfg or tmp_cfg()
        rm = RiskManager(cfg, store_for(cfg, capital))
        s = s or setup(stop=1.16910)
        bid, ask = QUOTES[s.symbol]
        return rm.evaluate(s, bid, ask, list(open_trades), capital, capital, MIDS, T0)

    def test_size_grows_and_shrinks_with_capital(self):
        units = {c: self.verdict(c).units for c in (40, 50, 60, 75, 100)}
        self.assertTrue(units[40] < units[50] < units[60] < units[75] < units[100], units)
        for c in (50, 60, 75, 100):
            self.assertAlmostEqual(self.verdict(c).risk_eur, c * 0.01, delta=0.01)

    def test_missing_or_wrong_side_stop_refused(self):
        self.assertFalse(self.verdict(50, setup(stop=float("nan"))).approved)
        self.assertFalse(self.verdict(50, setup(stop=1.17050)).approved)   # stop au-dessus d'un achat

    def test_stop_bounds_and_rr(self):
        self.assertFalse(self.verdict(50, setup(stop=1.16995)).approved)   # 1,5 pip < 3 pips min
        self.assertFalse(self.verdict(50, setup(stop=1.16700)).approved)   # 31 pips > 20 max
        self.assertFalse(self.verdict(50, setup(stop=1.16910, target=1.17100)).approved)   # R:R 0,9

    def test_max_two_positions_and_same_symbol(self):
        two = [trade_row(), trade_row("USDJPY", "SELL", 148.0, 148.1, 500, 14)]
        v = self.verdict(50, setup("GBPUSD", "SELL", 1.34, 1.3410, 1.3380), two)
        self.assertFalse(v.approved)
        self.assertIn("positions", v.reasons[0])
        v = self.verdict(50, open_trades=[trade_row()])
        self.assertIn("déjà ouverte", v.reasons[0])

    def test_correlated_exposure_blocked(self):
        # long EURUSD ouvert = short USD ; long GBPUSD ajouterait encore du short USD
        v = self.verdict(50, setup("GBPUSD", "BUY", 1.34012, 1.33900, 1.34300), [trade_row()])
        self.assertFalse(v.approved)
        self.assertIn("corrélé", v.reasons[0])

    def test_total_risk_cap(self):
        big = trade_row(entry=1.17010, stop=1.16910, units=1100)       # ~0,94 € de risque ouvert
        v = self.verdict(50, setup("USDJPY", "BUY", 148.012, 147.90, 148.30), [big])
        self.assertFalse(v.approved)
        self.assertIn("risque total", v.reasons[0])

    def test_margin_reduces_size_never_increases_risk(self):
        v = self.verdict(50, setup(stop=1.16960))                        # stop 5 pips -> gros nominal
        self.assertTrue(v.approved)
        self.assertIn("réduite par la marge", v.reasons[0])
        self.assertLessEqual(v.risk_eur, 0.5)
        self.assertLessEqual(v.margin_eur, 50 * 0.6 + 1e-9)


class RiskStateTest(unittest.TestCase):
    def _close_trades(self, store, pnls):
        for i, p in enumerate(pnls):
            t = T0 - timedelta(minutes=30 - i)
            store.insert_trade(symbol="EURUSD", direction="BUY", strategy="T", entry=1, stop=0.99, initial_stop=0.99,
                               target=1.02, units=1, risk_eur=0.5, entry_time=t.isoformat(),
                               exit_time=t.isoformat(), pnl_eur=p, status="closed")

    def test_no_martingale_risk_only_decreases_after_losses(self):
        cfg = tmp_cfg()
        store = store_for(cfg)
        rm = RiskManager(cfg, store)
        self.assertEqual(rm.risk_pct(), 1.0)
        self._close_trades(store, [-0.5, -0.5])
        self.assertEqual(rm.risk_pct(), 0.5)
        self._close_trades(store, [0.8])
        self.assertEqual(rm.risk_pct(), 1.0)                            # revient au standard, jamais au-dessus

    def test_cooldown_after_three_losses(self):
        cfg = tmp_cfg()
        store = store_for(cfg)
        self._close_trades(store, [-0.3, -0.3, -0.3])
        ok, why = RiskManager(cfg, store).trading_allowed(T0, 49.1)
        self.assertFalse(ok)
        self.assertIn("anti-revenge", why)

    def test_daily_loss_limit(self):
        cfg = tmp_cfg()
        store = store_for(cfg)
        self._close_trades(store, [-1.0, 0.1, -0.7])
        ok, why = RiskManager(cfg, store).trading_allowed(T0, 48.4)
        self.assertFalse(ok)
        self.assertIn("journalière", why)

    def test_kill_switch_on_drawdown(self):
        cfg = tmp_cfg()
        store = store_for(cfg)
        rm = RiskManager(cfg, store)
        ok, why = rm.trading_allowed(T0, 39.0)                          # -22 % depuis 50
        self.assertFalse(ok)
        self.assertTrue(rm.kill_path.exists())

    def test_stop_can_only_tighten(self):
        cfg = tmp_cfg()
        rm = RiskManager(cfg, store_for(cfg))
        t = trade_row()
        self.assertFalse(rm.validate_stop_move(t, 1.16900, BID, ASK)[0])      # élargir
        self.assertFalse(rm.validate_stop_move(t, None, BID, ASK)[0])         # supprimer
        self.assertFalse(rm.validate_stop_move(t, 1.17005, BID, ASK)[0])      # au-delà du prix
        self.assertTrue(rm.validate_stop_move(t, 1.16950, BID, ASK)[0])       # resserrer


if __name__ == "__main__":
    unittest.main()
