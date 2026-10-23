"""Contrôles du moteur : prix d'exécution, priorité du stop, timing des signaux, sorties à l'heure."""
import numpy as np
import pandas as pd

from forex_lab.engine import Rules, Simulator, resample, run_bar_strategy


def m1_frame(n=600, start="2025-03-03 00:00", price=1.1000, spread=0.0001, path=None):
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    mid = np.full(n, price) if path is None else np.asarray(path, float)
    df = pd.DataFrame({"bid_open": mid, "bid_high": mid + 0.00005, "bid_low": mid - 0.00005, "bid_close": mid}, index=idx)
    for c in ("open", "high", "low", "close"):
        df[f"ask_{c}"] = df[f"bid_{c}"] + spread
    return df


def test_spread_cost_flat_market():
    sim = Simulator("EURUSD", m1_frame())
    tr = sim.run_position(1, pd.Timestamp("2025-03-03 01:00", tz="UTC"), Rules(cap_min=30))
    assert abs(tr.pips + 1.0) < 1e-6 and tr.reason == "temps"          # achat à l'ask, sortie au bid = −1 pip
    assert tr.exit_time == pd.Timestamp("2025-03-03 01:30", tz="UTC")


def test_stop_first_when_both_hit_same_minute():
    df = m1_frame()
    k = 70
    df.iloc[k, df.columns.get_loc("bid_high")] = 1.1100
    df.iloc[k, df.columns.get_loc("bid_low")] = 1.0900
    sim = Simulator("EURUSD", df)
    tr = sim.run_position(1, pd.Timestamp("2025-03-03 01:00", tz="UTC"), Rules(sl_pips=20, tp_pips=20))
    assert tr.reason == "stop" and tr.pips < 0


def test_signal_entry_next_bar_open_and_no_lookahead():
    path = np.r_[np.full(300, 1.1000), np.linspace(1.1000, 1.1100, 300)]
    df = m1_frame(path=path)
    bars = resample(df, 60)
    sig = np.zeros(len(bars), bool)
    sig[2] = True                                                      # signal à la clôture de la bougie 02:00-03:00
    sim = Simulator("EURUSD", df)
    trades = run_bar_strategy(sim, bars, sig, np.zeros(len(bars), bool), Rules(max_bars=1), 60)
    assert trades[0].entry_time == pd.Timestamp("2025-03-03 03:00", tz="UTC")
    assert abs(trades[0].entry - (df.loc[trades[0].entry_time, "ask_open"])) < 1e-12


def test_flat_hour_projet():
    sim = Simulator("EURUSD", m1_frame(n=1500, start="2025-03-03 19:00"))
    tr = sim.run_position(-1, pd.Timestamp("2025-03-03 20:30", tz="UTC"), Rules(cap_min=240, flat_utc_hour=21))
    assert tr.exit_time == pd.Timestamp("2025-03-03 21:00", tz="UTC")


# ---------------- audit V3 (23/10/2026) ----------------
from forex_lab.engine import Costs, Event, run_portfolio, pip_value_usd_per_lot
from forex_lab.reference import reference_trade


def test_sell_prices_and_spread():
    sim = Simulator("EURUSD", m1_frame())
    tr = sim.run_position(-1, pd.Timestamp("2025-03-03 01:00", tz="UTC"), Rules(cap_min=10))
    assert abs(tr.entry - 1.1000) < 1e-12 and abs(tr.exit - 1.1001) < 1e-12 and abs(tr.pips + 1.0) < 1e-6


def test_stop_gap_fills_at_open_not_at_stop():
    df = m1_frame()
    k = 80                                                             # gap défavorable : ouverture sous le stop
    for c in ("open", "high", "low", "close"):
        df.iloc[k, df.columns.get_loc(f"bid_{c}")] = 1.0950
        df.iloc[k, df.columns.get_loc(f"ask_{c}")] = 1.0951
    sim = Simulator("EURUSD", df)
    tr = sim.run_position(1, pd.Timestamp("2025-03-03 01:00", tz="UTC"), Rules(sl_pips=10))
    assert tr.reason == "stop" and abs(tr.exit - 1.0950) < 1e-12


def test_costs_commission_and_slippage():
    assert pip_value_usd_per_lot("EURUSD", 1.1) == 10.0
    assert abs(pip_value_usd_per_lot("USDJPY", 150.0) - 6.6667) < 1e-3
    sim = Simulator("EURUSD", m1_frame(), Costs(commission_usd_per_lot_side=3.0, slippage_pips=0.1))
    tr = sim.run_position(1, pd.Timestamp("2025-03-03 01:00", tz="UTC"), Rules(cap_min=30))
    assert abs(tr.cost_pips - (0.6 + 0.2)) < 1e-9 and abs(tr.pips - (tr.gross_pips - 0.8)) < 1e-9


def test_end_of_data_position_is_closed_not_dropped():
    sim = Simulator("EURUSD", m1_frame(n=100))
    tr = sim.run_position(1, pd.Timestamp("2025-03-03 01:00", tz="UTC"), Rules())
    assert tr is not None and tr.reason == "fin"


def test_portfolio_max_two_positions():
    sims = {s: Simulator(s, m1_frame()) for s in ("EURUSD", "GBPUSD", "USDJPY")}
    t = pd.Timestamp("2025-03-03 01:00", tz="UTC")
    evs = [Event(t, s, 1, Rules(cap_min=60)) for s in ("EURUSD", "GBPUSD", "USDJPY")]
    evs.append(Event(t + pd.Timedelta(minutes=30), "EURUSD", 1, Rules(cap_min=60)))   # paire occupée
    evs.append(Event(t + pd.Timedelta(minutes=61), "USDJPY", 1, Rules(cap_min=60)))   # place libérée
    trades = run_portfolio(evs, sims, max_open=2)
    assert [x.pair for x in trades] == ["EURUSD", "GBPUSD", "USDJPY"]
    assert trades[2].entry_time == t + pd.Timedelta(minutes=61)


def test_reference_simulator_agrees_with_engine():
    rng = np.random.default_rng(3)
    path = 1.1 + np.cumsum(rng.normal(0, 0.00008, 3000))
    df = m1_frame(n=3000, path=path)
    df["bid_high"] = df["bid_close"] + rng.uniform(0, 0.0003, 3000)
    df["bid_low"] = df["bid_close"] - rng.uniform(0, 0.0003, 3000)
    for c in ("high", "low"):
        df[f"ask_{c}"] = df[f"bid_{c}"] + 0.0001
    sim = Simulator("EURUSD", df)
    for i in range(200):
        t = df.index[int(rng.integers(0, 2500))]
        side = int(rng.choice([-1, 1]))
        sl, tp, cap = float(rng.choice([5, 10])), float(rng.choice([5, 15])), int(rng.choice([15, 120]))
        e = sim.run_position(side, t, Rules(sl_pips=sl, tp_pips=tp, cap_min=cap))
        r = reference_trade(df, "EURUSD", side, t, sl, tp, t + pd.Timedelta(minutes=cap))
        assert e.exit_time == r["exit_time"] and abs(e.exit - r["exit"]) < 1e-12 and e.reason == r["reason"]


def test_signals_have_no_lookahead():
    """Les signaux d'une bougie ne doivent pas changer quand on ajoute des données futures."""
    from forex_lab.strategies import BAR_STRATEGIES
    rng = np.random.default_rng(5)
    path = 1.1 + np.cumsum(rng.normal(0, 0.0002, 20000))
    df = m1_frame(n=20000, path=path)
    for cid, (fn, tf, _, _) in BAR_STRATEGIES.items():
        bars = resample(df, tf)
        cut = len(bars) * 2 // 3
        full = [np.asarray(x.fillna(False))[:cut] if x is not None else None for x in fn(bars, "EURUSD")]
        part = [np.asarray(x.fillna(False)) if x is not None else None for x in fn(bars.iloc[:cut], "EURUSD")]
        for a, b in zip(full, part):
            if a is not None:
                assert (a == b).all(), cid


def test_new_york_schedule_follows_dst():
    from forex_lab.strategies import f03_trades
    df = m1_frame(n=60 * 24 * 12, start="2025-03-03 00:00")          # couvre le passage à l'heure d'été US (9 mars)
    sim = Simulator("EURUSD", df)
    trades = f03_trades(sim, df.index[0], df.index[-1], "exact")
    shorts = {tr.entry_time.date(): tr.entry_time.hour for tr in trades if tr.side < 0}
    assert shorts[pd.Timestamp("2025-03-07").date()] == 8                # 03:00 New York = 08:00 UTC (hiver)
    assert shorts[pd.Timestamp("2025-03-10").date()] == 7                # 03:00 New York = 07:00 UTC (été)


def test_fixed_price_stop_and_r_multiple_target():
    path = np.r_[np.full(100, 1.1000), np.linspace(1.1000, 1.1050, 200)]
    sim = Simulator("EURUSD", m1_frame(n=300, path=path))
    t = pd.Timestamp("2025-03-03 01:00", tz="UTC")
    tr = sim.run_position(1, t, Rules(cap_min=240), sl_price=1.0980, tp_r=1.0)
    risk = tr.entry - 1.0980
    assert tr.reason == "objectif" and abs((tr.exit - tr.entry) - risk) < 1e-12
    assert sim.run_position(1, t, Rules(cap_min=240), sl_price=1.1050) is None   # entrée déjà sous le « stop »


def test_scheduled_reversal_in_same_minute_is_kept():
    sims = {"EURUSD": Simulator("EURUSD", m1_frame())}
    t0, t1, t2 = (pd.Timestamp(x, tz="UTC") for x in ("2025-03-03 01:00", "2025-03-03 02:00", "2025-03-03 03:00"))
    evs = [Event(t0, "EURUSD", -1, Rules(), hard_exit=t1, chain=True), Event(t1, "EURUSD", 1, Rules(), hard_exit=t2, chain=True)]
    trades = run_portfolio(evs, sims, 2)
    assert len(trades) == 2 and trades[1].entry_time == t1
    # sans « chain », un signal dans la minute de sortie reste refusé (comportement des EA MetaTrader)
    evs2 = [Event(t0, "EURUSD", -1, Rules(), hard_exit=t1), Event(t1, "EURUSD", 1, Rules(), hard_exit=t2)]
    assert len(run_portfolio(evs2, sims, 2)) == 1


def test_tokyo_paper_windows():
    from forex_lab.v3 import h1_exact_events
    ev = h1_exact_events(pd.Timestamp("2025-01-05", tz="UTC"), pd.Timestamp("2025-01-08", tz="UTC"))
    buy, sell = ev[0], ev[1]
    assert buy.time == pd.Timestamp("2025-01-05 22:00", tz="UTC")       # 17:00 New York (hiver) la veille
    assert buy.hard_exit == sell.time == pd.Timestamp("2025-01-06 00:55", tz="UTC")
    assert sell.hard_exit == pd.Timestamp("2025-01-06 07:00", tz="UTC")  # 02:00 New York (hiver)
