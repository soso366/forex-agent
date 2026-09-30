import json
import unittest
from datetime import datetime, timedelta

import pandas as pd
from helpers import T0, UTC, flat_m1, simple_provider, store_for, tmp_cfg

from forex_agent.brain.llm import LLMBrain, validate
from forex_agent.cycle import run_cycle
from forex_agent.data.providers import InMemoryProvider, SyntheticProvider, market_open_at, validate_m1
from forex_agent.scheduler import cycle_time, next_run, replay


class DataTest(unittest.TestCase):
    def test_no_look_ahead_only_closed_candles(self):
        p = simple_provider()
        now = T0 + timedelta(minutes=7)                       # 10:07
        m5 = p.candles("EURUSD", "M5", now, 5)
        self.assertEqual(m5.index[-1], pd.Timestamp(T0))      # la bougie 10:05 n'est pas clôturée
        m1 = p.candles("EURUSD", "M1", now, 3)
        self.assertEqual(m1.index[-1], pd.Timestamp(now - timedelta(minutes=1)))
        h1 = p.candles("EURUSD", "H1", T0 + timedelta(minutes=59), 5)
        self.assertEqual(h1.index[-1], pd.Timestamp(T0 - timedelta(hours=1)))

    def test_quote_is_open_of_current_minute(self):
        path = [(1.17, 1.17, 1.17, 1.17)] * 60 + [(1.1705, 1.171, 1.170, 1.1708)]
        p = simple_provider(EURUSD=path)
        self.assertEqual(p.quote("EURUSD", T0), (1.1705, 1.1705 + 0.0001))

    def test_invalid_data_rejected(self):
        df = flat_m1("EURUSD", T0, 10, 1.17, 0.0001)
        df.loc[df.index[3], "ac"] = 1.1690                    # ask < bid
        with self.assertRaises(ValueError):
            validate_m1(df, "EURUSD")

    def test_weekend_closed(self):
        self.assertFalse(market_open_at(datetime(2026, 9, 11, 21, 30, tzinfo=UTC)))   # vendredi soir
        self.assertFalse(market_open_at(datetime(2026, 9, 12, 12, 0, tzinfo=UTC)))    # samedi
        self.assertFalse(market_open_at(datetime(2026, 9, 13, 20, 0, tzinfo=UTC)))    # dimanche avant 21h
        self.assertTrue(market_open_at(datetime(2026, 9, 13, 21, 5, tzinfo=UTC)))
        self.assertTrue(market_open_at(T0))


class SchedulerTest(unittest.TestCase):
    def test_next_run_aligned_every_5_minutes(self):
        at = lambda h, m, s=0: datetime(2026, 9, 9, h, m, s, tzinfo=UTC)
        self.assertEqual(next_run(at(10, 2, 30), 5, 15), at(10, 5, 15))
        self.assertEqual(next_run(at(10, 0, 5), 5, 15), at(10, 0, 15))
        self.assertEqual(next_run(at(10, 57, 0), 5, 15), at(11, 0, 15))
        self.assertEqual(cycle_time(at(10, 7, 40), 5), at(10, 5))


class LLMGuardrailTest(unittest.TestCase):
    def test_llm_cannot_invent_a_trade(self):
        with self.assertRaises(ValueError):
            validate('{"new_trade": {"candidate_id": "zzz"}}', {"abc"}, set())

    def test_llm_has_no_size_field_and_bad_actions_dropped(self):
        out = validate(json.dumps({
            "new_trade": {"candidate_id": "abc", "reason": "superbe", "size": 100000, "risk_pct": 50},
            "positions": [{"trade_id": 1, "action": "DOUBLE_DOWN"}, {"trade_id": 1, "action": "HOLD"}],
        }), {"abc"}, {1})
        self.assertNotIn("size", out["new_trade"])
        self.assertEqual([p["action"] for p in out["positions"]], ["HOLD"])

    def test_llm_disabled_without_key_falls_back(self):
        cfg = tmp_cfg(llm={"enabled": True, "api_key_env": "NO_SUCH_KEY_XYZ", "model": "x", "max_tokens": 10})
        brain = LLMBrain(cfg)
        self.assertFalse(brain.enabled)
        self.assertIn("déterministes", brain.status)


class CycleTest(unittest.TestCase):
    def test_cycle_logged_even_without_trade(self):
        cfg = tmp_cfg()
        start = T0 - timedelta(days=4)
        prov = SyntheticProvider(["EURUSD", "GBPUSD", "USDJPY"], start - timedelta(days=2), T0 + timedelta(days=1))
        store = store_for(cfg)
        rec = run_cycle(cfg, prov, store, T0)
        self.assertIsNone(rec["error"])
        rows = store.db.execute("SELECT symbol, regime, decision, reason FROM market_snapshots").fetchall()
        self.assertEqual({r["symbol"] for r in rows}, {"EURUSD", "GBPUSD", "USDJPY"})
        self.assertTrue(all(r["decision"] and r["reason"] for r in rows))

    def test_llm_wide_stop_request_is_refused(self):
        class FakeLLM:
            def complete(self, system, user):
                p = json.loads(user)
                return json.dumps({"new_trade": {"candidate_id": None, "reason": "rien de propre"},
                                   "positions": [{"trade_id": t["id"], "action": "MOVE_STOP",
                                                  "new_stop": t["stop"] - 0.0050, "reason": "laisser respirer"}
                                                 for t in p["open_positions"]],
                                   "ideas": ["tester un filtre de killzone"]})
        cfg = tmp_cfg(llm={"enabled": True, "model": "x", "max_tokens": 10})
        prov = SyntheticProvider(["EURUSD", "GBPUSD", "USDJPY"], T0 - timedelta(days=6), T0 + timedelta(days=1))
        store = store_for(cfg)
        from forex_agent.broker.paper import PaperBroker
        tid = PaperBroker(store, prov, cfg).open("EURUSD", "BUY", 300, prov.quote("EURUSD", T0)[0] - 0.0010,
                                                 prov.quote("EURUSD", T0)[0] + 0.0030, 0.3, 10, "Test_v1",
                                                 "test", "{}", T0)
        rec = run_cycle(cfg, prov, store, T0 + timedelta(minutes=5), LLMBrain(cfg, FakeLLM()))
        t = store.trade(tid)
        self.assertEqual(t["stop"], t["initial_stop"])            # le stop n'a pas été élargi
        self.assertEqual(rec["llm_status"], "ok")
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM ideas").fetchone()[0], 1)

    def test_autonomous_replay_invariants(self):
        """Un jour complet de cycles : jamais plus de 2 positions, jamais plus de 30 min."""
        cfg = tmp_cfg(trading={"min_confirmations": 6})       # un peu plus permissif pour générer des trades
        start = datetime(2026, 9, 14, 6, 0, tzinfo=UTC)
        prov = SyntheticProvider(["EURUSD", "GBPUSD", "USDJPY"], datetime(2026, 9, 8, tzinfo=UTC),
                                 datetime(2026, 9, 16, tzinfo=UTC), seed=11)
        recs = replay(cfg, start, start + timedelta(hours=14), provider=prov)
        self.assertEqual(len(recs), 14 * 12 + 1)
        self.assertTrue(all(r["error"] is None for r in recs))
        self.assertTrue(all(len(r["open_positions"]) <= 2 for r in recs))
        from forex_agent.journal import Store
        store = Store(cfg["paths"]["db"])
        closed = store.closed_trades()
        self.assertTrue(all(t["duration_min"] <= 30 for t in closed))
        peak = float(store.account()["peak_equity"])
        self.assertTrue(all(t["risk_eur"] <= 0.01 * peak + 1e-9 for t in closed))
        self.assertGreater(len(closed), 0, "le rejeu devrait produire au moins un trade")


if __name__ == "__main__":
    unittest.main()
