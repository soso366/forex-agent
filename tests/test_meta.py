"""Meta-skills : informatifs, sans effet sur les décisions."""
import unittest
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from forex_agent.meta import exposure, journal_audit


class TestExposure(unittest.TestCase):
    def test_legs(self):
        self.assertEqual(exposure.legs("EURUSD", "BUY", 1.0), {"EUR": 1.0, "USD": -1.0})
        self.assertEqual(exposure.legs("USDJPY", "SELL", 2.0), {"USD": -2.0, "JPY": 2.0})

    def test_same_usd_exposure_flagged(self):
        class P:
            def candles(self, sym, tf, now, n):
                raise RuntimeError("pas de données")
        a = exposure.audit({"symbol": "GBPUSD", "direction": "BUY", "risk_eur": 0.5},
                           [{"symbol": "EURUSD", "direction": "BUY", "risk_eur": 0.5}], P(),
                           datetime(2026, 6, 10, 13, tzinfo=timezone.utc), {"news": {"auto_nfp": False}})
        self.assertEqual(a["net_exposure_eur"]["USD"], -1.0)
        self.assertEqual(a["pairs"][0]["same_direction"], ["USD"])
        self.assertTrue(any("même exposition USD" in n for n in a["notes"]))
        self.assertIsNone(a["pairs"][0]["pnl_corr_5d"])          # données absentes : pas d'invention

    def test_no_open_trade(self):
        self.assertFalse(exposure.audit({"symbol": "EURUSD", "direction": "BUY", "risk_eur": 1}, [], None,
                                        datetime.now(timezone.utc), {})["applies"])


class TestJournalAudit(unittest.TestCase):
    def frame(self, n=40):
        rng = np.random.default_rng(0)
        t0 = datetime(2026, 3, 2, 8, tzinfo=timezone.utc)
        rows = []
        for i in range(n):
            et = t0 + timedelta(hours=7 * i)
            r = float(rng.choice([-1.0, -0.4, 0.3, 1.2]))
            rows.append({"symbol": ["EURUSD", "GBPUSD", "USDJPY"][i % 3], "direction": "BUY",
                         "strategy": "S_perd" if i % 2 else "S_autre", "entry_time": et.isoformat(),
                         "exit_time": (et + timedelta(minutes=30)).isoformat(), "duration_min": 30.0,
                         "exit_reason": "TIME_STOP : 30 min", "r_multiple": r - (0.6 if i % 2 else 0),
                         "mfe_r": max(r, 0) + 0.6, "mae_r": 0.5, "session": "london", "regime": "RANGE",
                         "entry": 1.1, "initial_stop": 1.099, "exit_price": 1.1, "pnl_eur": r})
        return pd.DataFrame(rows)

    def test_observations_are_not_rules(self):
        res = journal_audit.audit(journal_audit.prepare(self.frame()))
        self.assertEqual(res["global"]["n"], 40)
        self.assertIn("JAMAIS une règle", res["rule"])
        self.assertTrue(res["observations"])
        for o in res["observations"]:
            self.assertIn(o["statut"], ("échantillon insuffisant : ne rien conclure",
                                        "hypothèse à tester (backtest → validation → OOS)"))
        md = journal_audit.to_markdown(res)
        self.assertIn("pas des règles", md)

    def test_empty(self):
        self.assertEqual(journal_audit.audit(pd.DataFrame())["n"], 0)


if __name__ == "__main__":
    unittest.main()
